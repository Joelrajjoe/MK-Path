import logging
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

logger = logging.getLogger("mkpath.database")
logging.basicConfig(level=logging.INFO)

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_online = False

    async def connect(self):
        if not settings.MONGODB_URI:
            logger.warning("MONGODB_URI is not set. Database is operating in OFFLINE/DEMO mode.")
            self.is_online = False
            return False

        try:
            # Set client with a fast 3-second server selection timeout
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=3000
            )
            self.db = self.client[settings.MONGODB_DATABASE]

            # Ping to verify Atlas connection
            await self.client.admin.command("ping")
            self.is_online = True
            logger.info("Successfully connected to MongoDB Atlas!")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}. Gracefully switching to OFFLINE/DEMO mode.")
            self.client = None
            self.db = None
            self.is_online = False
            return False

    def get_collection(self, name: str):
        """
        Retrieve a collection lazily.
        Returns the motor Collection object if database is online, otherwise returns None.
        """
        if self.is_online and self.db is not None:
            return self.db[name]
        return None

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB Atlas connection closed.")
            self.is_online = False

db_manager = DatabaseManager()

async def get_db():
    # Attempt lazy connection if client is not initialized and we haven't failed connection
    if db_manager.client is None and not db_manager.is_online:
        await db_manager.connect()
    return db_manager
