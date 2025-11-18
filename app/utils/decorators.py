"""Security and audit decorators."""
from functools import wraps
from flask import abort, current_app
from flask_login import current_user

from app.models.user import AccessLevel, Role
from app.models.audit import AuditLog


def require_access_level(*levels):
    """Decorator to require minimum access level."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            # Convert levels to AccessLevel enums if they're strings
            required_levels = []
            for level in levels:
                if isinstance(level, str):
                    required_levels.append(AccessLevel[level.upper()])
                elif isinstance(level, AccessLevel):
                    required_levels.append(level)

            if current_user.access_level not in required_levels:
                current_app.logger.warning(
                    f"Access denied for user {current_user.username} "
                    f"(level: {current_user.access_level.value}) "
                    f"to access {f.__name__}"
                )
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(*roles):
    """Decorator to require specific role(s)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            # Convert roles to Role enums if they're strings
            required_roles = []
            for role in roles:
                if isinstance(role, str):
                    required_roles.append(Role[role.upper()])
                elif isinstance(role, Role):
                    required_roles.append(role)

            if current_user.role not in required_roles:
                current_app.logger.warning(
                    f"Access denied for user {current_user.username} "
                    f"(role: {current_user.role.value}) "
                    f"to access {f.__name__}"
                )
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_action(action, resource_type):
    """Decorator to automatically audit actions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resource_id = kwargs.get('id') or kwargs.get('customer_id') or kwargs.get('opportunity_id')
            success = True
            error_message = None
            result = None

            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Log the action
                if current_user.is_authenticated:
                    try:
                        AuditLog.log_action(
                            user=current_user,
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            description=f"{action} {resource_type}",
                            success=success,
                            error_message=error_message
                        )
                    except Exception as audit_error:
                        current_app.logger.error(f"Audit logging failed: {audit_error}")

        return decorated_function
    return decorator


def sensitive_data_access(f):
    """Decorator to log access to sensitive data (high net worth, full account numbers)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)

        if current_user.is_authenticated:
            try:
                AuditLog.log_action(
                    user=current_user,
                    action='view_sensitive',
                    resource_type='sensitive_data',
                    description=f"Accessed sensitive data in {f.__name__}"
                )
            except Exception as e:
                current_app.logger.error(f"Sensitive data audit failed: {e}")

        return result
    return decorated_function
