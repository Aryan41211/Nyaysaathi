"""
db_connection.py – MongoDB singleton for NyaySaathi
"""
import logging
from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)
_client = None

def get_client():
    global _client
    if _client is None:
        try:
            _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command("ping")
            logger.info("MongoDB connected: %s", settings.MONGODB_URI)
        except ConnectionFailure as e:
            logger.error("MongoDB connection failed: %s", e)
            raise
    return _client

def get_db():
    return get_client()[settings.MONGODB_DB]

def get_collection(name):
    return get_db()[name]
