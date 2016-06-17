import time
from pymongo import MongoClient

class MongoAccess:
    def __init__(self, dbName, collectionName):
        # Create collection object
        self.collection = ((MongoClient())[dbName])[collectionName]
        
        # Write saying start/initialisation time in epoch
        self.write({"atype":"START", "ver":"1.0", "ts":time.time()
                    , "comment":"Writing has started"})
    
    def write(self, value):
        # write value to collection
        return self.collection.insert(value)