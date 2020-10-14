#!/usr/bin/python3
from lapse import *
import sys
DEFAULT_INTERVAL = 120  # 2 minutes
DEFAULT_DURATION = 60*60*24  # 24 Hours

if __name__ == "__main__":
    cr = CameraRemote()
    tl = Timelapse(cr)

    args = sys.argv[1:]
    argcount = len(args)
    interval = args[0] if argcount > 0 else DEFAULT_INTERVAL
    duration = args[1] if argcount > 1 else DEFAULT_DURATION

    tl.start(interval=int(interval), duration=int(duration))
