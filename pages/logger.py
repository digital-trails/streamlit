import time

class Logger:
    def __init__(self, path: str):
        self.path = path

    def log(self, event: str, description: str = ""):
        with open(self.path,'at') as logfile:
            logfile.write(f"""
{time.time()} event {event}: 
{description}

""")