from __future__ import annotations

import os
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    db_name = os.getenv("MONGODB_DB", "nyaysaathi")
    return get_mongo_client()[db_name]


def get_users_collection() -> Collection:
    return get_database()["users"]


def get_queries_collection() -> Collection:
    return get_database()["user_queries"]


def get_workflows_collection() -> Collection:
    return get_database()["legal_workflows_multilingual"]


def get_cache_collection() -> Collection:
    return get_database()["classification_cache"]


def get_feedback_collection() -> Collection:
    return get_database()["feedback"]
