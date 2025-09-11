from flask import Blueprint, render_template, request
from services.audit_service import log_action
from flask_login import login_required, current_user
from models.audit_log import AuditLog
from datetime import datetime, timedelta

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/audit-logs')
@login_required
def audit_logs():
    log_action('View Audit Logs Tab', 'Viewed audit logs')
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 20
    max_pages = 5
    # Date range filter
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    now = datetime.utcnow()
    # Default: last 10 minutes
    if not from_date and not to_date:
        from_dt = now - timedelta(minutes=10)
        to_dt = now
    else:
        from_dt = datetime.strptime(from_date, '%Y-%m-%dT%H:%M') if from_date else now - timedelta(days=365)
        to_dt = datetime.strptime(to_date, '%Y-%m-%dT%H:%M') if to_date else now
    query = AuditLog.query.filter(AuditLog.timestamp >= from_dt, AuditLog.timestamp <= to_dt)
    total_logs = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset((page-1)*per_page).limit(per_page).all()
    # Always pass max_pages, page, from_date, to_date
    return render_template(
        'audit_logs.html',
        logs=logs,
        page=page,
        max_pages=max_pages,
        from_date=from_date or from_dt.strftime('%Y-%m-%dT%H:%M'),
        to_date=to_date or to_dt.strftime('%Y-%m-%dT%H:%M')
    )
