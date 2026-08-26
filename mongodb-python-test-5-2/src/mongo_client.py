from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

def get_db():
    client = MongoClient("mongodb://localhost:27017/")
    return client["minishop"]