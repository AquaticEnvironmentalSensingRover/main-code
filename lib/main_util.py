from datetime import datetime

def generateTimeName(start= "AESR_", end= "", format = "%Y%m%dT%H%M%S"):
        return datetime.now().strftime(start + format + end)