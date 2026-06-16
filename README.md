# Videoflix – Backend

Django REST API backend for the Videoflix Netflix-clone project.

## Tech Stack

- **Django 6 + Django REST Framework** — REST API
- **PostgreSQL** — primary database
- **Redis + django-redis** — caching layer
- **Django RQ** — background task queue for ffmpeg video conversion
- **Simple JWT** — cookie-based JWT authentication
- **FFMPEG** — HLS video conversion (480p / 720p / 1080p)
- **Gunicorn + WhiteNoise** — production server and static file serving
- **Docker + Docker Compose** — containerised deployment

## Getting Started

### Prerequisites

- Docker and Docker Compose installed

### Setup

1. Copy the environment template and fill in your values:

```bash
cp .env.template .env
```

2. Start all services:

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.  
The Django admin is at `http://localhost:8000/admin/` (superuser is created automatically from `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD`).

## Account Activation

After registration the account is inactive until confirmed via email.

**Local testing** (`EMAIL_BACKEND=console`, `DEBUG=True`):  
The activation link is printed to the Docker logs — copy it from there and open it in the browser:

```bash
docker logs videoflix_backend
```

The link calls the backend directly:
`http://localhost:8000/api/activate/<uidb64>/<token>/`

**Production** (`DEBUG=False`):  
The link points to the Angular frontend (`FRONTEND_URL`), which forwards the token to the backend.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Debug mode (`True` / `False`) | `False` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `localhost` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins | — |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `http://localhost:4200` |
| `DJANGO_SUPERUSER_EMAIL` | Admin account email (auto-created) | `admin@example.com` |
| `DJANGO_SUPERUSER_PASSWORD` | Admin account password (auto-created) | `adminpassword` |
| `DB_NAME` | PostgreSQL database name | `videoflix_db` |
| `DB_USER` | PostgreSQL user | `videoflix_user` |
| `DB_PASSWORD` | PostgreSQL password | — |
| `DB_HOST` | PostgreSQL host | `db` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `REDIS_LOCATION` | Redis URL for cache | `redis://redis:6379/1` |
| `REDIS_HOST` | Redis host for RQ | `redis` |
| `REDIS_PORT` | Redis port for RQ | `6379` |
| `EMAIL_BACKEND` | Django email backend class | `smtp.EmailBackend` |
| `EMAIL_HOST` | SMTP server | — |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP user | — |
| `EMAIL_HOST_PASSWORD` | SMTP password | — |
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@videoflix.com` |
| `FRONTEND_URL` | Angular frontend base URL (emails in production) | `http://localhost:4200` |
| `BACKEND_URL` | Backend base URL (activation emails in development) | `http://localhost:8000` |

## API Endpoints

### Authentication

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/register/` | Register a new user |
| `GET` | `/api/activate/<uidb64>/<token>/` | Activate account via email link |
| `POST` | `/api/login/` | Login — sets JWT cookies |
| `POST` | `/api/logout/` | Logout — clears cookies, blacklists refresh token |
| `POST` | `/api/token/refresh/` | Refresh access token cookie |
| `POST` | `/api/password_reset/` | Request password reset email |
| `POST` | `/api/password_confirm/<uidb64>/<token>/` | Set new password |

### Video

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/video/` | List all videos with genre and thumbnail |
| `GET` | `/api/video/<id>/<resolution>/index.m3u8` | HLS manifest for a video |
| `GET` | `/api/video/<id>/<resolution>/<segment>/` | HLS `.ts` segment |

All video endpoints require JWT authentication (cookie).

## Video Processing

When a `Video` object is saved via the Django admin, Django RQ automatically enqueues three ffmpeg jobs to produce HLS streams at 480p, 720p and 1080p. Output files are stored under `media/videos/<id>/<resolution>/`.

## Running Tests

```bash
docker-compose run --rm web python manage.py test --settings=videoflix.test_settings
```
