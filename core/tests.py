import os
import shutil
import tempfile
from http.cookies import SimpleCookie
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Genre, Video
from core.tasks import convert_to_hls
from core.utils import get_hls_output_path

CACHE_OVERRIDE = override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)


def make_active_user():
    from users.models import CustomUser
    user = CustomUser.objects.create_user(email='core@test.com', password='Pass123!')
    user.is_active = True
    user.save()
    return user


def auth_client(client, user):
    refresh = RefreshToken.for_user(user)
    client.cookies = SimpleCookie({'access_token': str(refresh.access_token)})
    return client


def make_video(title='Test Video', genre=None):
    fake_file = SimpleUploadedFile('test.mp4', b'fake-video-content', content_type='video/mp4')
    return Video.objects.create(title=title, genre=genre, video_file=fake_file)


# ---------------------------------------------------------------------------
# Genre Model
# ---------------------------------------------------------------------------

class GenreModelTest(TestCase):
    def test_str(self):
        g = Genre.objects.create(name='Action')
        self.assertEqual(str(g), 'Action')

    def test_name_unique(self):
        Genre.objects.create(name='Drama')
        with self.assertRaises(Exception):
            Genre.objects.create(name='Drama')

    def test_max_length(self):
        g = Genre.objects.create(name='A' * 100)
        self.assertEqual(len(g.name), 100)


# ---------------------------------------------------------------------------
# Video Model
# ---------------------------------------------------------------------------

@patch('core.signals.django_rq.get_queue')
class VideoModelTest(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name='Comedy')

    def test_str(self, mock_queue):
        mock_queue.return_value = MagicMock()
        v = make_video(title='My Movie', genre=self.genre)
        self.assertEqual(str(v), 'My Movie')

    def test_defaults(self, mock_queue):
        mock_queue.return_value = MagicMock()
        v = make_video()
        self.assertIsNotNone(v.created_at)
        self.assertEqual(v.description, '')

    def test_genre_fk(self, mock_queue):
        mock_queue.return_value = MagicMock()
        v = make_video(genre=self.genre)
        self.assertEqual(v.genre.name, 'Comedy')

    def test_genre_set_null_on_delete(self, mock_queue):
        mock_queue.return_value = MagicMock()
        v = make_video(genre=self.genre)
        self.genre.delete()
        v.refresh_from_db()
        self.assertIsNone(v.genre)

    def test_ordering_newest_first(self, mock_queue):
        mock_queue.return_value = MagicMock()
        v1 = make_video(title='First')
        v2 = make_video(title='Second')
        videos = list(Video.objects.all())
        self.assertEqual(videos[0].pk, v2.pk)


# ---------------------------------------------------------------------------
# Core Utils
# ---------------------------------------------------------------------------

class CoreUtilsTest(TestCase):
    def test_get_hls_output_path_contains_id_and_resolution(self):
        path = get_hls_output_path(42, '720p')
        self.assertIn('42', path)
        self.assertIn('720p', path)

    def test_get_hls_output_path_is_string(self):
        path = get_hls_output_path(1, '480p')
        self.assertIsInstance(path, str)

    def test_get_hls_output_path_is_absolute(self):
        path = get_hls_output_path(1, '480p')
        self.assertTrue(os.path.isabs(path))


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class ConvertToHLSTaskTest(TestCase):
    @patch('core.tasks.subprocess.run')
    @patch('core.tasks.os.makedirs')
    def test_calls_ffmpeg(self, mock_makedirs, mock_run):
        convert_to_hls(1, '/src/video.mp4', '720p', 720)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn('ffmpeg', cmd)
        self.assertIn('/src/video.mp4', cmd)
        self.assertIn('scale=-2:720', cmd)

    @patch('core.tasks.subprocess.run')
    @patch('core.tasks.os.makedirs')
    def test_creates_output_dir(self, mock_makedirs, mock_run):
        convert_to_hls(1, '/src/video.mp4', '480p', 480)
        mock_makedirs.assert_called_once()
        args = mock_makedirs.call_args
        self.assertTrue(args[1].get('exist_ok', False))

    @patch('core.tasks.subprocess.run', side_effect=Exception('ffmpeg not found'))
    @patch('core.tasks.os.makedirs')
    def test_propagates_subprocess_error(self, mock_makedirs, mock_run):
        with self.assertRaises(Exception):
            convert_to_hls(1, '/src/video.mp4', '1080p', 1080)

    @patch('core.tasks.subprocess.run')
    @patch('core.tasks.os.makedirs')
    def test_output_path_contains_resolution(self, mock_makedirs, mock_run):
        convert_to_hls(5, '/src/video.mp4', '1080p', 1080)
        cmd = mock_run.call_args[0][0]
        self.assertTrue(any('1080p' in str(arg) for arg in cmd))


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class VideoPostSaveSignalTest(TestCase):
    @patch('core.signals.django_rq.get_queue')
    def test_enqueues_three_resolutions_on_create(self, mock_get_queue):
        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue
        make_video()
        self.assertEqual(mock_queue.enqueue.call_count, 3)

    @patch('core.signals.django_rq.get_queue')
    def test_enqueues_all_resolutions(self, mock_get_queue):
        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue
        make_video()
        enqueue_calls = mock_queue.enqueue.call_args_list
        resolutions = [c[0][3] for c in enqueue_calls]
        self.assertIn('480p', resolutions)
        self.assertIn('720p', resolutions)
        self.assertIn('1080p', resolutions)

    @patch('core.signals.django_rq.get_queue')
    def test_no_enqueue_on_update(self, mock_get_queue):
        mock_queue = MagicMock()
        mock_get_queue.return_value = mock_queue
        video = make_video()
        mock_queue.enqueue.reset_mock()
        video.title = 'Updated'
        video.save()
        mock_queue.enqueue.assert_not_called()


class VideoPostDeleteSignalTest(TestCase):
    """
    setUp creates the video BEFORE any test-method @patch decorators are active,
    so Django's storage code sees real os.path functions. Each test then calls
    self.video.delete() while the os mocks ARE active (only the signal runs
    filesystem code during delete, not Django's storage layer).
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_dir)
        self.media_override.enable()
        with patch('core.signals.django_rq.get_queue', return_value=MagicMock()):
            self.video = make_video()

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('core.signals.django_rq.get_queue')
    @patch('core.signals.shutil.rmtree')
    @patch('core.signals.os.path.isdir', return_value=True)
    @patch('core.signals.os.remove')
    @patch('core.signals.os.path.isfile', return_value=True)
    def test_deletes_video_file(self, mock_isfile, mock_remove, mock_isdir, mock_rmtree, mock_queue):
        mock_queue.return_value = MagicMock()
        self.video.delete()
        mock_remove.assert_called()

    @patch('core.signals.django_rq.get_queue')
    @patch('core.signals.shutil.rmtree')
    @patch('core.signals.os.path.isdir', return_value=True)
    @patch('core.signals.os.remove')
    @patch('core.signals.os.path.isfile', return_value=True)
    def test_removes_hls_directory(self, mock_isfile, mock_remove, mock_isdir, mock_rmtree, mock_queue):
        mock_queue.return_value = MagicMock()
        self.video.delete()
        mock_rmtree.assert_called_once()

    @patch('core.signals.django_rq.get_queue')
    @patch('core.signals.shutil.rmtree')
    @patch('core.signals.os.path.isdir', return_value=False)
    @patch('core.signals.os.remove')
    @patch('core.signals.os.path.isfile', return_value=False)
    def test_no_remove_when_files_missing(self, mock_isfile, mock_remove, mock_isdir, mock_rmtree, mock_queue):
        mock_queue.return_value = MagicMock()
        self.video.delete()
        mock_remove.assert_not_called()
        mock_rmtree.assert_not_called()


# ---------------------------------------------------------------------------
# VideoSerializer
# ---------------------------------------------------------------------------

@patch('core.signals.django_rq.get_queue')
class VideoSerializerTest(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name='Thriller')

    def test_category_field_returns_genre_name(self, mock_queue):
        from core.api.serializers import VideoSerializer
        mock_queue.return_value = MagicMock()
        video = make_video(genre=self.genre)
        data = VideoSerializer(video, context={'request': None}).data
        self.assertEqual(data['category'], 'Thriller')

    def test_category_none_without_genre(self, mock_queue):
        from core.api.serializers import VideoSerializer
        mock_queue.return_value = MagicMock()
        video = make_video()
        data = VideoSerializer(video, context={'request': None}).data
        self.assertIsNone(data['category'])

    def test_fields_present(self, mock_queue):
        from core.api.serializers import VideoSerializer
        mock_queue.return_value = MagicMock()
        video = make_video()
        data = VideoSerializer(video, context={'request': None}).data
        for field in ['id', 'title', 'description', 'category', 'created_at']:
            self.assertIn(field, data)

    def test_video_file_not_exposed(self, mock_queue):
        from core.api.serializers import VideoSerializer
        mock_queue.return_value = MagicMock()
        video = make_video()
        data = VideoSerializer(video, context={'request': None}).data
        self.assertNotIn('video_file', data)


# ---------------------------------------------------------------------------
# VideoListView
# ---------------------------------------------------------------------------

@patch('core.signals.django_rq.get_queue')
@CACHE_OVERRIDE
class VideoListViewTest(APITestCase):
    URL = reverse('video-list')

    def setUp(self):
        self.user = make_active_user()

    def test_unauthenticated_returns_403(self, mock_queue):
        mock_queue.return_value = MagicMock()
        r = self.client.get(self.URL)
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_authenticated_returns_200(self, mock_queue):
        mock_queue.return_value = MagicMock()
        auth_client(self.client, self.user)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_returns_list(self, mock_queue):
        mock_queue.return_value = MagicMock()
        make_video(title='V1')
        make_video(title='V2')
        auth_client(self.client, self.user)
        r = self.client.get(self.URL)
        self.assertEqual(len(r.data), 2)

    def test_empty_list(self, mock_queue):
        mock_queue.return_value = MagicMock()
        auth_client(self.client, self.user)
        r = self.client.get(self.URL)
        self.assertEqual(r.data, [])

    def test_category_in_response(self, mock_queue):
        mock_queue.return_value = MagicMock()
        genre = Genre.objects.create(name='Horror')
        make_video(genre=genre)
        auth_client(self.client, self.user)
        r = self.client.get(self.URL)
        self.assertEqual(r.data[0]['category'], 'Horror')


# ---------------------------------------------------------------------------
# HLSManifestView
# ---------------------------------------------------------------------------

@patch('core.signals.django_rq.get_queue')
class HLSManifestViewTest(APITestCase):
    """
    Each test gets a fresh MEDIA_ROOT (temp dir) so leftover manifest files
    from test_existing_manifest_200 cannot pollute test_missing_manifest_file_404.
    """

    def setUp(self):
        self.user = make_active_user()
        self.temp_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_dir)
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _url(self, video_id, resolution):
        return reverse('hls-manifest', args=[video_id, resolution])

    def test_unauthenticated_403(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        r = self.client.get(self._url(video.pk, '720p'))
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_invalid_resolution_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '360p'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_video_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(99999, '720p'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_manifest_file_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '720p'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_existing_manifest_200(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        manifest_dir = get_hls_output_path(video.pk, '720p')
        os.makedirs(manifest_dir, exist_ok=True)
        manifest_path = os.path.join(manifest_dir, 'index.m3u8')
        with open(manifest_path, 'w') as f:
            f.write('#EXTM3U\n')
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '720p'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_all_valid_resolutions_accepted(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        auth_client(self.client, self.user)
        for res in ['480p', '720p', '1080p']:
            r = self.client.get(self._url(video.pk, res))
            self.assertNotEqual(r.status_code, status.HTTP_400_BAD_REQUEST, f'Resolution {res} rejected')


# ---------------------------------------------------------------------------
# HLSSegmentView
# ---------------------------------------------------------------------------

@patch('core.signals.django_rq.get_queue')
class HLSSegmentViewTest(APITestCase):
    """Per-test MEDIA_ROOT prevents segment files from leaking across tests."""

    def setUp(self):
        self.user = make_active_user()
        self.temp_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_dir)
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _url(self, video_id, resolution, segment):
        return reverse('hls-segment', args=[video_id, resolution, segment])

    def test_unauthenticated_403(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        r = self.client.get(self._url(video.pk, '720p', '000.ts'))
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_invalid_resolution_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '360p', '000.ts'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_segment_pattern_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '720p', 'evil_segment.ts'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_segment_file_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '720p', '000.ts'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_video_404(self, mock_queue):
        mock_queue.return_value = MagicMock()
        auth_client(self.client, self.user)
        r = self.client.get(self._url(99999, '720p', '000.ts'))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_segment_200(self, mock_queue):
        mock_queue.return_value = MagicMock()
        video = make_video()
        segment_dir = get_hls_output_path(video.pk, '720p')
        os.makedirs(segment_dir, exist_ok=True)
        segment_path = os.path.join(segment_dir, '000.ts')
        with open(segment_path, 'wb') as f:
            f.write(b'\x00' * 16)
        auth_client(self.client, self.user)
        r = self.client.get(self._url(video.pk, '720p', '000.ts'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
