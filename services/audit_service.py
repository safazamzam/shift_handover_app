from models.audit_log import AuditLog
from flask_login import current_user
from models.models import db
from flask import request

def log_action(action, details=None):
    user_id = getattr(current_user, 'id', None)
    username = getattr(current_user, 'username', None)
    db.session.add(AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        details=details or f"Path: {request.path}"
    ))
    db.session.commit()
