import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base Configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///instance/database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    
    # Upload / Download
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', 'downloads')
    TEMP_FOLDER = os.getenv('TEMP_FOLDER', 'temp')
    
    # Rate Limiting
    MAX_DOWNLOADS_PER_HOUR = int(os.getenv('MAX_DOWNLOADS_PER_HOUR', 50))
    MAX_DOWNLOADS_PER_DAY = int(os.getenv('MAX_DOWNLOADS_PER_DAY', 200))
    
    # File Retention
    FILE_RETENTION_HOURS = int(os.getenv('FILE_RETENTION_HOURS', 24))
    
    # Queue
    QUEUE_MAX_SIZE = int(os.getenv('QUEUE_MAX_SIZE', 100))
    
    # API Keys
    SSSTIK_COOKIE = os.getenv('SSSTIK_COOKIE', '')
    
    # Redis (for Celery)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    
    # Features
    ENABLE_BATCH_DOWNLOAD = os.getenv('ENABLE_BATCH_DOWNLOAD', 'True').lower() == 'true'
    ENABLE_4K_UPSCALE = os.getenv('ENABLE_4K_UPSCALE', 'True').lower() == 'true'
    ENABLE_USER_SYSTEM = os.getenv('ENABLE_USER_SYSTEM', 'True').lower() == 'true'
    
    # Default Settings
    DEFAULT_QUALITY = os.getenv('DEFAULT_QUALITY', '4K')
    DEFAULT_API = os.getenv('DEFAULT_API', 'tikwm')
    DEFAULT_UPSCALE_METHOD = os.getenv('DEFAULT_UPSCALE_METHOD', 'lanczos')

class ProductionConfig(Config):
    """Production Configuration"""
    DEBUG = False
    TESTING = False
    
class DevelopmentConfig(Config):
    """Development Configuration"""
    DEBUG = True
    TESTING = True
    
class TestingConfig(Config):
    """Testing Configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
