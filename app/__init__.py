"""Flask application factory."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_babel import Babel

from config import config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
babel = Babel()


def get_locale():
    """Determine the best locale for the current request."""
    # Try to get language from user's preference
    if current_user.is_authenticated and hasattr(current_user, 'language'):
        return current_user.language or 'bs'
    # Try to get language from session
    if 'language' in session:
        return session['language']
    # Fallback to default
    return 'bs'


def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance and log directories exist
    Path(app.config['LOG_DIR']).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app, locale_selector=get_locale)

    # Configure Babel
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    app.config['BABEL_DEFAULT_LOCALE'] = 'bs'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['bs', 'en', 'tr']

    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Molimo prijavite se za pristup ovoj stranici.'
    login_manager.login_message_category = 'info'

    # Setup logging
    setup_logging(app)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.customers import customers_bp
    from app.blueprints.opportunities import opportunities_bp
    from app.blueprints.activities import activities_bp
    from app.blueprints.targets import targets_bp
    from app.blueprints.analytics import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(opportunities_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(targets_bp)
    app.register_blueprint(analytics_bp)

    # Register error handlers
    register_error_handlers(app)

    # Register template filters and context processors
    register_template_helpers(app)

    return app


def setup_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # File handler for general logs
        log_file = Path(app.config['LOG_DIR']) / 'crm_ub.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)

        # File handler for audit logs
        audit_log_file = Path(app.config['LOG_DIR']) / 'audit.log'
        audit_handler = RotatingFileHandler(
            audit_log_file,
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        audit_handler.setLevel(logging.INFO)

        # Create separate logger for audit
        audit_logger = logging.getLogger('audit')
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)

    app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
    app.logger.info('Universal Bank CRM startup')


def register_error_handlers(app):
    """Register error handlers."""
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.error(f'Internal error: {e}')
        return render_template('errors/500.html'), 500


def register_template_helpers(app):
    """Register template filters and context processors."""
    from datetime import datetime
    from flask import current_app
    import json
    from pathlib import Path

    # Load translations
    translations_file = Path(app.root_path) / 'translations_json' / 'messages.json'
    with open(translations_file, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    def get_translation(key, lang=None):
        """Get translation for a key."""
        if lang is None:
            lang = get_locale()
        return translations.get(lang, {}).get(key, key)

    @app.template_filter('datetime')
    def format_datetime(value, format='%d.%m.%Y %H:%M'):
        """Format datetime for display."""
        if value is None:
            return ''
        return value.strftime(format)

    @app.template_filter('date')
    def format_date(value, format='%d.%m.%Y'):
        """Format date for display."""
        if value is None:
            return ''
        return value.strftime(format)

    @app.template_filter('t')
    def translate(key):
        """Translate a key to current language."""
        return get_translation(key)

    @app.context_processor
    def utility_processor():
        """Add utility functions to template context."""
        return {
            'now': datetime.utcnow,
            'app_name': current_app.config.get('APP_NAME', 'CRM'),
            't': get_translation
        }
