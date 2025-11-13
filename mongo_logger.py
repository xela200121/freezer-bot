import logging
import sys
import os
from datetime import datetime
from pymongo import MongoClient, ASCENDING


# Recupera URI MongoDB dall'env
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "freezer-bot"
COLLECTION_NAME = "logs"

# =========================
# MongoDB Handler
# =========================
class MongoHandler(logging.Handler):
    """Custom logging handler that saves logs to MongoDB"""
    
    def __init__(self, mongo_uri=MONGODB_URI, db_name=DB_NAME, collection_name=COLLECTION_NAME):
        super().__init__()
        self.client = MongoClient(mongo_uri)
        self.collection = self.client[db_name][collection_name]
        self._ensure_ttl_index()

    def _ensure_ttl_index(self, expire_seconds=604800):
        """
        Crea un indice TTL basato sul campo 'timestamp' per eliminare automaticamente i documenti.
        Di default elimina dopo 7 giorni (604800 secondi)
        """
        try:
            self.collection.create_index(
                [("timestamp", ASCENDING)],
                expireAfterSeconds=expire_seconds
            )
        except Exception as e:
            print(f"❌ Errore creazione indice TTL: {e}")

    def emit(self, record):
        log_entry = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": datetime.utcnow()
        }
        try:
            self.collection.insert_one(log_entry)
        except Exception as e:
            print(f"❌ Errore salvataggio log su Mongo: {e}")

# =========================
# Interceptor per print()
# =========================
class PrintInterceptor:
    """Redirect stdout/stderr to logger"""
    def __init__(self, logger):
        self.logger = logger

    def write(self, msg):
        msg = msg.strip()
        if msg:
            self.logger.info(msg)

    def flush(self):
        pass

# =========================
# Setup logger globale
# =========================
logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Mongo handler
mongo_handler = MongoHandler()
mongo_handler.setLevel(logging.INFO)
mongo_handler.setFormatter(formatter)
logger.addHandler(mongo_handler)

# Redirect print() e stderr
sys.stdout = PrintInterceptor(logger)
sys.stderr = PrintInterceptor(logger)

# =========================
# TEST RAPIDO
# =========================
if __name__ == "__main__":
    print("✅ Interceptor avviato!")
    logger.info("🔹 Test log info")
    logger.error("❌ Test log error")
