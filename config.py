import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-do-not-use-in-prod')
    
    # Support multiple comma-separated keys for pooling
    _raw_keys = os.environ.get('ROUTER_API_KEY', '')
    ROUTER_API_KEYS = [k.strip() for k in _raw_keys.split(',') if k.strip()]
    
    # Keep the first key as the default for fallback
    ROUTER_API_KEY = ROUTER_API_KEYS[0] if ROUTER_API_KEYS else None
    
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'dockets.db')
    
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    EXPORT_FOLDER = os.path.join(BASE_DIR, 'exports')
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    
    @classmethod
    def init_app(cls):
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.EXPORT_FOLDER, exist_ok=True)
