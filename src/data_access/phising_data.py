import pandas as pd
from src.configuration.mongo_db_connection import MongoDBClient


class PhisingData:
    def __init__(self, database_name):
        self.connection = MongoDBClient(database_name)
        self.database = self.connection.database

    def get_collection_names(self):
        return self.database.list_collection_names()

    def get_collection_data(self, collection_name):
        return pd.DataFrame(list(self.database[collection_name].find({}, {'_id': 0})))

    def export_collections_as_dataframe(self):
        for name in self.get_collection_names():
            yield name, self.get_collection_data(name)
