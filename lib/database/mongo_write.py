import time
from pymongo import MongoClient

class MongoWrite:
    def __init__(self, db, collection, *args, **kwargs):
        # Create collection object
        self.collection = ((MongoClient(*args, **kwargs))[db])[collection]
        
        # Write saying start/initialisation time in epoch
        self.write({"atype":"START", "ver":"1.0", "ts":time.time()
                    , "comment":"Writing has started"})
    
    def write(self, value):
        # write value to collection
        return self.collection.insert(value)