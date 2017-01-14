import pymongo

class mongodb(object):
    def __init__(self, collection):
        self.MONGO_HOST = 'localhost'
        self.MONGO_PORT = 27017
        self.MONGO_DB = 'Spider'
        self.COLLECTION = collection
        self.client = pymongo.MongoClient(self.MONGO_HOST, self.MONGO_PORT)
        self.db = self.client[self.MONGO_DB]

    def insert(self, item):
        self.db[self.COLLECTION].insert(item)
        return item

    def clean(self):
        self.db[self.COLLECTION].drop()

    def count(self):
        return self.db[self.COLLECTION].count()

    def close_db(self):
        self.client.close()