import os
import sys
import time
import datetime
import subprocess
from contextlib import contextmanager
import gphoto2 as gp
from PIL import Image, ImageChops, ImageFilter, ImageDraw
import numpy as np
import utils

FRAMES_DIR = "static/frames"
DIFFS_DIR = "static/diffs"
OVERLAYS_DIR = "static/overlays"
TL_LOG = "logs/timelapse.log"
STDOUT = sys.stdout

# Example usage:
#
# cr = CameraRemote()
# tl = Timelapse(cr)
# tl.start(interval=5, duration=60*15)   // run the timelapse for 15 minutes
# ...
# trace_motion()   // generate black and white "difference" images between frames
# overlay_motion_trace() // use the above difference frames to mask the timelapse frames

def make_preview_video_of_latest_n_frames(n):
    ...

def osx_permission_fix():
    if os.uname().sysname == "Darwin":
        subprocess.run(["killall", "PTPCamera"])

def linux_permission_fix():
    if os.uname()[0] == "Linux":
        subprocess.run(["pkill", "-f", "gphoto2"])

class CameraRemote:
    '''
    Simplified API (using gphoto2) to control a DSLR (e.g. Nikon D60) over USB.
    '''
    F_NUMBERS = [4.8, 5, 5.6, 6.3, 7.1, 8, 9, 10, 11, 13, 14, 16, 18, 20, 22, 25, 29, 32]
    SHUTTER_SPEEDS = []

    def __init__(self, verbose=False):
        self.cam = self._init_session(verbose)
        self.cfg = self.cam.get_config()
        self.capture_settings = CaptureSetting(self.fstop, self.shutterspeed)

    def _init_session(self, verbose=True):
        osx_permission_fix()
        linux_permission_fix()
        camera = gp.Camera()
        camera.init()
        if verbose:
            print(camera.get_summary())
        else:
            print("Camera initialized.")
        return camera

    @contextmanager
    def camera_config(self):
        '''
        Used for keeping camera state updated and in sync with program.
        '''
        try:
            cfg = self.cam.get_config()
            capture_settings = cfg.get_child_by_name("capturesettings")
            yield capture_settings
        finally:
            self.cam.set_config(cfg)

    @property       # Convenience mutators for common properties.
    def fstop(self):
        return self.get_capture_setting("f-number")

    @fstop.setter
    def fstop(self, val):
        self.set_capture_setting("f-number", val)

    @property
    def shutterspeed(self):
        return self.get_capture_setting("shutterspeed2")

    @shutterspeed.setter
    def shutterspeed(self, val):
        self.set_capture_setting("shutterspeed2", val)

    @property
    def exposure(self):
        ...
        #return self.get_capture_setting("exposure")
    
    def slower(self):
        self.capture_settings.shutter_speed_down()
    def faster(self):
        self.capture_settings.shutter_speed_up()

    def print_capture_settings(self):
        ''' 
        Get and display capture settings from camera.
        '''
        with self.camera_config() as camera:
            for setting in camera.get_children():
                print(setting.get_name(), " : ", setting.get_value())

    def get_capture_setting(self, name):    # Read from camera.
        with self.camera_config() as camera:
            return camera.get_child_by_name(name).get_value()

    def set_capture_setting(self, name, val):    # Write to camera.
        with self.camera_config() as camera:
            field = camera.get_child_by_name(name)
            print(field, "****debug")
            field.set_value(val)
        print(f"{name} set to {val}")

    def capture(self, filename):
        ''' 
        Take a photo. Transfer to computer. Delete from camera.
        '''
        path = self.cam.capture(gp.GP_CAPTURE_IMAGE)
        cam_file = self.cam.file_get(path.folder, path.name, gp.GP_FILE_TYPE_NORMAL)
        cam_file.save(filename)
        self.cam.file_delete(path.folder, path.name)

    def wait_for_event(self, timeout=10):  # timeout in milliseconds
        while True:
            type_, data = self.cam.wait_for_event(timeout)
            #print('waiting for camera...', end="\r")
            if type_ == gp.GP_EVENT_TIMEOUT:
                #print("event: timeout")
                return
            if type_ == gp.GP_EVENT_FILE_ADDED:
                print("event: file added event.", file=STDOUT)
            if type_ == gp.GP_EVENT_CAPTURE_COMPLETE:
                print("event: capture completed.", file=STDOUT)

    def free(self):
        ''' Free camera resource. '''
        self.cam.exit()

class Timelapse:
    FRAME_TMPL = "frame%04d.jpg"

    def __init__(self, cam_remote: CameraRemote, frames_dir=FRAMES_DIR, logfile=None):
        self.cam_remote = cam_remote
        self.frames_dir = frames_dir
        self.logfile = logfile
        self._setup()

    def _setup(self):
        if not os.path.exists(self.frames_dir):
            os.makedirs(self.frames_dir)
        self.frame_template = os.path.join(self.frames_dir, self.FRAME_TMPL)
        self.log = sys.stdout if self.logfile is None else open(self.logfile, "a")

    def start(self, interval=10, duration=None):
        count = 1
        started = time.time()
        next_shot = started + 1
        if duration == None:
            duration = started + 60 * 60 * 24 * 365 # run for a year

        print("Timelapse starting... \n\t Interval:  %s \n\t Duration:  %s"
                % (get_display_dur(interval), get_display_dur(duration)) )

        while True:
            try:
                self.cam_remote.wait_for_event()    # Avoid filling camera buffer
                while True:    # Stay in sync with timelapse interval
                    delay = next_shot - time.time()
                    if delay < 0:
                        break
                    time.sleep(delay)
                
                while True: # Main capture-attempt loop
                    try:
                        self.cam_remote.capture(filename=self.frame_template % count)
                        break
                    except gp.GPhoto2Error as e:
                        if e.code == gp.GP_ERROR_CAMERA_BUSY:
                            utils.log(logfile=TL_LOG, msg="{}, count: {}, error:{} -- {}".format(
                                                        datetime.datetime.now(), count, e.code, e.string))
                            print("Camera was busy, waiting for event...", file=STDOUT)
                            self.cam_remote.wait_for_event()
                        else:
                            self.error = e
                            utils.log(logfile=TL_LOG, msg="{}, count: {}, error:{} -- {}".format(
                                                        datetime.datetime.now(), count, e.code, e.string))
                            print("Uncaught Error:", e.string, file=STDOUT)
                            self.cam_remote.wait_for_event()
                            # testing this..... !TODO fix and handle gphoto2 errors here better
                            #self.cam_remote.free()
                            #raise e

                print("captured frame # ", count, file=STDOUT)  # Advance count and elapsed time
                next_shot += interval
                count += 1
                elapsed_time = time.time() - started

                if elapsed_time > duration:
                    break

            except KeyboardInterrupt:
                print("Timelapse ended.", file=STDOUT)
                break
        print("Timelapse finished.", file=STDOUT)
        self.cam_remote.free()  # free camera USB resource
        if self.log != sys.stdout:
            self.log.close()

# Example usage, run a timelapse.
def run(interval=10, duration=5*60): # e.g., capture photo every 10 seconds for 5 minutes
    cr = CameraRemote()
    timelapse = Timelapse(cam_remote=cr, frames_dir=FRAMES_DIR)
    timelapse.start()

#######
# Image processing for motion detection
#######

class MotionDetector:

    def __init__(self, frames_dir=FRAMES_DIR):
        self.frames_dir = frames_dir
        self.q = self.get_new_frames()

    def get_new_frames(self):
        ...

def binarize(im, threshold=64, scale_factor=4, outfile='binarized.png'):
    bw_thumb_pixels = np.array(im.convert('L').resize(
                    (int(im.width/scale_factor), int(im.height/scale_factor))))
    binarized = (bw_thumb_pixels > threshold) * 255
    binarized = Image.fromarray(np.uint8(binarized))
    binarized.save(outfile)
    return binarized

def draw_outline(im):
    outlined = ImageDraw.Draw(im)
    outlined.rectangle(im.getbbox(), fill=None, outline="red")
    im.save('outlined.png')
    return im

def boxblur(im):
    blurred = im.filter(ImageFilter.BoxBlur(radius=1))
    return blurred

def boxblur_smoother(im):
    #smoothed = im.filter(ImageFilter.SMOOTH)
    #smoothed = smoothed.filter(ImageFilter.SMOOTH_MORE)
    blurred = smoothed.filter(ImageFilter.BoxBlur(radius=1))
    return blurred

def bin_sheet(im, threshold_sequence=[2, 4, 8, 16, 32, 64, 128], outfile='bin_strip.png'):
    bw_thumb_pixels = np.array(im.convert('L').resize(
                    (int(im.width/4), int(im.height/4))))
    bins = []
    for thresh in threshold_sequence:
        binarization = (bw_thumb_pixels > thresh) * 255
        bins.append(binarization)
    im_strip = np.concatenate(bins, axis=1)
    Image.fromarray(np.uint8(im_strip)).save(outfile)

def detect_changed_area(a: Image, b: Image):
    diff = ImageChops.difference(b, a)
    binarized = binarize(diff, threshold=64, scale_factor=4)
    blurred = boxblur(binarized)
    re_binarized = binarize(blurred, threshold=64, scale_factor=1)
    outlined = draw_outline(re_binarized)
    return (outlined.resize((outlined.width*4, outlined.height*4)),
            re_binarized.getbbox())

def trace_motion(frames_dir):
    if not os.path.exists(DIFFS_DIR):
        os.makedirs(DIFFS_DIR)
    TMP = os.path.join(DIFFS_DIR, "difference_%04d.png")
    frames = deque(os.path.join(frames_dir, file_name)
                     for file_name in os.listdir(frames_dir))
    prev = Image.open(frames.popleft())
    count = 1
    while frames:
        try:
            cur = frames.popleft()
        except IndexError:
            break
        cur = Image.open(cur)
        im, bbox = detect_changed_area(prev, cur)
        im.save(TMP % count)
        prev = cur
        count += 1
    print("Processed %d frames." % count, file=STDOUT)            
    return

def overlay_motion_trace(frames_dir, diffs_dir):
    OUT_TMP = os.path.join(OVERLAYS_DIR, "overlay_%04d.png")
    if not os.path.exists(OVERLAYS_DIR):
        os.makedirs(OVERLAYS_DIR)

    raw_frames = deque(os.path.join(frames_dir, file_name)
                        for file_name in os.listdir(frames_dir))
    diff_frames = deque(os.path.join(diffs_dir, file_name)
                        for file_name in os.listdir(diffs_dir))
                        
    cur_frame = Image.open(raw_frames.popleft())
    cur_frame.save(OUT_TMP % 0)
    
    markup_key_color = Image.new("RGB", cur_frame.size, (255, 0, 255)) # Magenta
    count = 1
    while raw_frames:
        raw = Image.open(raw_frames.popleft())
        diff = Image.open(diff_frames.popleft())
        comp = ImageChops.composite(image1=markup_key_color, image2=raw, mask=diff)
        comp.save(OUT_TMP % count)
        count += 1

##   Helper functions
def get_display_dur(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    formatted_duration = []
    for n, unit in zip([hours, minutes, seconds], ["hour", "minute", "second"]):
        if n > 0:
            if n > 1:
                unit += "s"
            formatted_duration.append("%d %s" % (n, unit))
    return ", ".join(formatted_duration) or "0 seconds"

class CaptureSetting:
    F_NUMBERS = [5.6, 6.3, 7.1, 8, 9, 10, 11, 13, 14, 16, 18, 20, 22, 25, 29, 32]
    SHUTTER_SPEEDS = ['30', '25', '20', '15', '13', '10', '8', '6', '5', '4', '3', '2', '1',
			'1/2', '1/3', '1/4', '1/5', '1/6', '1/8', '1/10', '1/13', '1/15', '1/20',
			'1/25', '1/30', '1/40', '1/50', '1/60', '1/80', '1/100', '1/125', '1/160',
			'1/200', '1/250', '1/320', '1/400', '1/500', '1/640', '1/800', '1/1000',
			'1/1250', '1/1600', '1/2000', '1/2500'] #, '1/3200', '1/4000']
    F_NUMBER_MAP = dict(zip(F_NUMBERS, range(len(F_NUMBERS))))
    SHUTTER_SPEED_MAP = dict(zip(SHUTTER_SPEEDS, range(len(SHUTTER_SPEEDS))))

    def __init__(self, f_number=10, shutter_speed='1/10', min_shutter_speed=10):
        if isinstance(f_number, str) and f_number.startswith("f/"):
            f_number = float(f_number.lstrip("f/"))
        try:
            self.f_number_index = self.F_NUMBER_MAP[f_number]
        except IndexError:
            raise "Invalid f-number: %r" % f_number
        try:
            self.shutter_speed_index = self.SHUTTER_SPEED_MAP[shutter_speed]
        except IndexError:
            raise "Invalid shutter speed: %r" % shutter_speed
        self.f_number = "f/" + str(f_number)
        self.shutter_speed = str(shutter_speed)

    def f_number_up(self):
        self.f_number_index = min(self.f_number_index + 1, len(self.F_NUMBERS) - 1)
        self.f_number = "f/" + self.F_NUMBERS[self.f_number_index]
    def f_number_down(self):
        self.f_number_index = max(0, self.f_number_index - 1)
        self.f_number = "f/" + self.F_NUMBERS[self.f_number_index]
    def shutter_speed_up(self):
        self.shutter_speed_index = min(self.shutter_speed_index + 1, len(self.SHUTTER_SPEEDS) - 1)
        self.shutter_speed = self.SHUTTER_SPEEDS[self.shutter_speed_index]
    def shutter_speed_down(self):
        self.shutter_speed_index = max(0, self.shutter_speed_index - 1)
        self.shutter_speed = self.SHUTTER_SPEEDS[self.shutter_speed_index]

    def exposure_matrix(self, cr: CameraRemote, single_f = None):
        if single_f and single_f in self.F_NUMBER_MAP: # Allow for a fixed f-number, varying only shutter speed.
            f_nums = [single_f]
        else:
            f_nums = self.F_NUMBERS
        count = 0
        def fname(fnum, speed):
            nonlocal count
            count += 1
            return "%03d_F%.1f_S%s.jpg" % (count, fnum, speed.replace("/", '-'))
        for fnum in reversed(f_nums):
            cr.fstop = "f/%.1f" % fnum
            for speed in reversed(self.SHUTTER_SPEEDS):
                cr.shutterspeed = speed
                cr.capture(fname(fnum, speed))
                print("F: %s, S: %s, file: %s" % (fnum, speed, fname(fnum, speed)))
                
