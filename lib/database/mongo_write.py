import time
from pymongo import MongoClient

class MongoWrite:
    def __init__(self, db, col, *args, **kwargs):
        # Create collection object
        self.dbCol = ((MongoClient(*args, **kwargs))[db])[col]
        
        # Write saying start/initialisation time in epoch
        self.write({"atype":"START", "ver":"1.0", "ts":time.time()
                    , "comment":"Writing has started"})
    
    def write(self, value):
        # write value to collection
        return self.dbCol.insert(value)