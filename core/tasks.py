import subprocess

def convert_480p_video(source):
    target = source + '_480p.mp4'
    cmd = ['ffmpeg', '-i', source, '-vf', 'scale=-2:480', target]
    subprocess.run(cmd)
