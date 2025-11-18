"""Application configuration."""
import os
from datetime import timedelta
from pathlib import Path

basedir = Path(__file__).parent.absolute()


class Config:
    """Base configuration."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{basedir / "instance" / "crm_ub.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Logging
    LOG_DIR = basedir / 'logs'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 10

    # Application
    APP_NAME = 'Universal Bank CRM'
    ITEMS_PER_PAGE = 25

    # Localization
    SUPPORTED_LANGUAGES = ['bs', 'hr', 'sr', 'en']
    DEFAULT_LANGUAGE = 'bs'
    TIMEZONE = 'Europe/Sarajevo'

    # Features
    ENABLE_AUDIT_LOG = True
    ENABLE_MONITORING = True
    ENABLE_OFFLINE_MODE = True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    # In production, SECRET_KEY must be set via environment variable
    # The base Config class already handles this with: os.environ.get('SECRET_KEY') or 'dev-secret-key...'
    # Just ensure it's overridden in production environment


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
