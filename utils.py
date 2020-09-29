# utils.py

def log(logfile, msg):
    with open(logfile, 'a') as f:
        f.writelines(msg + "\n")
