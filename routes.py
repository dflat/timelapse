from flask import Flask, render_template, url_for, session, jsonify, request
import os
import subprocess
import random
import json
import utils
from PIL import Image

app = Flask(__name__)
app.secret_key = b'dead'
VIDEO_DIR = "video"
GIF_DIR = "gifs"
FFMPEG_LOG = "logs/ffmpeg.log"
FFMPEG_BIT_RATE = "1M"
UI_DIR = "ui"

class Frame(dict):
    DIR = "frames"
    TMPL = "frame%04d.jpg"
    VID_NAME = 'preview.webm'
    VID_RATE = 20

    def __init__(self, number, url):
        dict.__init__(self, number=number, url=url)
        self.number = number
        self.url = url

@app.route('/')
def timelapse_page(max_displayed_frames=100):
    frame_filenames = os.listdir(os.path.join('static', Frame.DIR))
    count = 1
    frames = []
    for name in frame_filenames:
        frames.append(Frame(count, os.path.join("static", Frame.DIR, name)))
        count += 1
    session['displayed_frames'] = frames
    random_clip_number = random.randint(1, len(os.listdir('static/ui/welcome_clips')))
    session['welcome_video'] = os.path.join("static", UI_DIR, "welcome_clips", "vapor_%03d.webm" % random_clip_number)
#    session['video_preview'] = session.get('latest_video_preview', os.path.join('static', VIDEO_DIR, Frame.VID_NAME))
    return render_template("timelapse.html", frames=list(reversed(frames))[:max_displayed_frames],
                                            video_preview=session['welcome_video'])

@app.route('/api/listdir/<dirname>')
def api_listdir(dirname):
    files = os.listdir(os.path.join('static', dirname))
    displayed = session['displayed_frames']
    n_displayed = len(displayed)
    new_file_count = len(files) - n_displayed
    session['new_frames'] = []
    for i in range(new_file_count):
        url = os.path.join("static", Frame.DIR, files.pop())
        session['new_frames'].append(Frame(n_displayed + i+1, url))

    session['displayed_frames'].extend(session['new_frames'])
    return jsonify(session['new_frames'])

@app.route('/api/make_video_preview/<n_frames>')
def make_video_preview(n_frames):
    fps = request.args.get("fps", Frame.VID_RATE)
    n_frames = int(n_frames)
    force_overwrite = "-y"
    frames = os.listdir(os.path.join('static', 'frames'))
    start_number = max(1, len(frames) - n_frames)
    in_path = os.path.join('static', Frame.DIR, Frame.TMPL)
    out_path = os.path.join('static', VIDEO_DIR, "preview_" + str(random.randint(0, 2**20)) + ".webm")
    cmd = ['ffmpeg', '-r', str(fps), '-start_number', str(start_number), force_overwrite, '-i', in_path,
            '-vframes', str(n_frames), out_path]
#            '-r', str(fps), "-b:v", str(FFMPEG_BIT_RATE), '-bufsize', '1B', "-maxrate", "1B",  out_path]
    utils.log(logfile=FFMPEG_LOG, msg=" ".join(cmd))
    subprocess.check_call(cmd)    
    return out_path

@app.route('/api/make_gif_preview/<n_frames>')
def make_gif_preview(n_frames):
    files = [os.path.join("static/frames/", f) for f in os.listdir("static/frames/")][-int(n_frames):]
    ims = [Image.open(f) for f in files]
    out_path = os.path.join('static', GIF_DIR, "preview_" + str(random.randint(0, 2**20)) + ".gif")
    gif = ims[0].save(out_path, save_all=True, append_images=ims[1:], optimize=True, duration=200, loop=0)
    return out_path

