from flask import Flask, render_template, url_for, session, jsonify
import os
import subprocess
import random
import json
import utils

app = Flask(__name__)
app.secret_key = b'dead'
VIDEO_DIR = "video"
FFMPEG_LOG = "logs/ffmpeg.log"

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
def timelapse_page():
    frame_filenames = os.listdir(os.path.join('static', Frame.DIR))
    count = 1
    frames = []
    for name in frame_filenames:
        frames.append(Frame(count, os.path.join("static", Frame.DIR, name)))
        count += 1
    session['displayed_frames'] = frames
    session['video_preview'] = session.get('latest_video_preview', os.path.join('static', VIDEO_DIR, Frame.VID_NAME))
    print("session object from web page load (via browser):")
    print(session)
    return render_template("timelapse.html", frames=reversed(frames),
                                            video_preview = session['video_preview'])

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

@app.route('/api/make_video_preview/<max_frames>')
def make_video_preview(max_frames=40):
    max_frames = int(max_frames)
    force_overwrite = "-y"
    frames = os.listdir(os.path.join('static', 'frames'))
    start_number = max(1, len(frames) - max_frames)
    in_path = os.path.join('static', Frame.DIR, Frame.TMPL)
    out_path = os.path.join('static', VIDEO_DIR, "preview_" + str(random.randint(0, 2**20)) + ".webm")
    cmd = ['ffmpeg', '-start_number', str(start_number), force_overwrite, '-i', in_path, '-vframes', str(max_frames), 
            '-r', str(Frame.VID_RATE), out_path]
    utils.log(logfile=FFMPEG_LOG, msg=" ".join(cmd))
    subprocess.check_call(cmd)    
    session['latest_video_preview'] = out_path
    print("session object from api call (via xhr):")
    print(session)
    return session['latest_video_preview']

