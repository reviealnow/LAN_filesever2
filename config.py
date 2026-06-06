import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_FOLDER = BASE_DIR / "uploads"
DATABASE_PATH = INSTANCE_DIR / "lan_fileserver.db"


class Config:
    # Prefer an explicit SECRET_KEY from the environment (set this in
    # production so sessions survive restarts). Fall back to a random
    # per-process key so the old hardcoded default is never used.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE = DATABASE_PATH
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {
        "csv",
        "gif",
        "jpeg",
        "jpg",
        "json",
        "log",
        "pcap",
        "pcapng",
        "pdf",
        "png",
        "txt",
    }
