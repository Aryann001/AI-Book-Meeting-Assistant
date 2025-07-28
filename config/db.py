from pymongo import MongoClient
from pymongo.errors import (
    ConnectionFailure,
    ConfigurationError,
    ServerSelectionTimeoutError,
)
from fastapi import HTTPException
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)


class MongoDB:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")  # Force connection
            self.db = self.client[self.db_name]
            host, port = list(self.client.nodes)[0]
            logging.info(
                f"✅ Database connected successfully at host : {host}, port : {port}"
            )
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logging.error(f"❌ Database connection error: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
        except ConfigurationError as ce:
            logging.error(f"❌ Database configuration error: {ce}")
            raise HTTPException(status_code=500, detail="Database configuration error")
        except Exception as e:
            logging.error(f"❌ Unexpected Database error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected Database error")

    def close(self):
        if self.client:
            self.client.close()
            logging.info("🛑 Database connection closed.")


# Create a global instance (like a singleton)
db = MongoDB(uri=os.environ["DB_URI"], db_name="aryan")
