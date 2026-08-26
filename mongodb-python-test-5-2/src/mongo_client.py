from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

def get_db():
    client = MongoClient(
        "mongodb+srv://root:root@cluster0.lgjfzis.mongodb.net/"
    )
    return client["minishop"]