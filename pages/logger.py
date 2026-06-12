import time

class Logger:
    def __init__(self, path: str, model: str):
        self.path = path
        self.model = model

    def log(self, event: str, description: str = ""):
        with open(self.path,'at') as logfile:
            logfile.write(f"""
{time.time()} {event} -- {self.model} 
{description}
""")