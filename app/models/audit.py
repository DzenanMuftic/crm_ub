"""Audit logging for compliance and monitoring."""
from datetime import datetime
from flask import request
from app import db


class AuditLog(db.Model):
    """Immutable audit log for all sensitive operations."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)

    # User & Session
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=False)  # Denormalized for audit trail
    session_id = db.Column(db.String(100))

    # Action Details
    action = db.Column(db.String(50), nullable=False, index=True)  # 'view', 'create', 'update', 'delete', 'export'
    resource_type = db.Column(db.String(50), nullable=False, index=True)  # 'customer', 'opportunity', etc.
    resource_id = db.Column(db.Integer, index=True)
    description = db.Column(db.String(500))

    # Changes (for update actions)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)

    # Request Context
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.String(500))
    endpoint = db.Column(db.String(200))
    method = db.Column(db.String(10))

    # Result
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.String(500))

    # Timestamp (immutable)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship('User')

    def __repr__(self):
        return f'<AuditLog {self.username} {self.action} {self.resource_type} at {self.timestamp}>'

    @staticmethod
    def log_action(user, action, resource_type, resource_id=None, description=None,
                   old_values=None, new_values=None, success=True, error_message=None):
        """Create an audit log entry."""
        audit_entry = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else 'anonymous',
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message
        )

        # Capture request context if available
        if request:
            audit_entry.ip_address = request.remote_addr
            audit_entry.user_agent = request.headers.get('User-Agent', '')[:500]
            audit_entry.endpoint = request.endpoint
            audit_entry.method = request.method

        db.session.add(audit_entry)
        db.session.commit()

        # Also log to audit logger
        import logging
        audit_logger = logging.getLogger('audit')
        log_message = f"User: {audit_entry.username}, Action: {action}, Resource: {resource_type}:{resource_id}, Success: {success}"
        if error_message:
            log_message += f", Error: {error_message}"
        audit_logger.info(log_message)

        return audit_entry
