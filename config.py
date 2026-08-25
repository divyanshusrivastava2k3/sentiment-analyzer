"""Application configuration."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    # Set MONGO_URI env var to point at your MongoDB instance.
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.environ.get("MONGO_DB", "sentiment_analyzer")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB CSV uploads
    MODEL_NAME = os.environ.get(
        "SENTIMENT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest"
    )
