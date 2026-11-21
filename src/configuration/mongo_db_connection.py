import os
from pymongo import MongoClient
from src.constant import MONGO_DATABASE_NAME


class MongoDBClient:
    def __init__(self, database_name=MONGO_DATABASE_NAME):
        url = os.getenv('MONGO_DB_URL')
        if not url:
            raise ValueError('Provide --data training.csv or configure MONGO_DB_URL in .env.')
        self.client = MongoClient(url, serverSelectionTimeoutMS=5000)
        self.database = self.client[database_name]
        self.database_name = database_name
