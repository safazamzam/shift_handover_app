from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from flask import session
from models.models import Shift, Incident, ShiftKeyPoint, TeamMember
 
from datetime import datetime

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/handover-reports', methods=['GET'])
@login_required
def handover_reports():
    from app import db
    date_filter = request.args.get('date')
    shift_type_filter = request.args.get('shift_type')
    from models.models import Account, Team
    query = Shift.query
    account_id = None
    team_id = None
    accounts = []
    teams = []
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id') or session.get('selected_account_id')
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        team_id = request.args.get('team_id') or session.get('selected_team_id')
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id') or session.get('selected_team_id')
    else:
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
    if account_id:
        query = query.filter_by(account_id=account_id)
    # Only filter by team_id if it is set and not empty string
    if team_id:
        query = query.filter_by(team_id=team_id)
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=date_obj)
        except Exception:
            pass
    if shift_type_filter:
        query = query.filter_by(current_shift_type=shift_type_filter)
    # Show both sent and draft handovers
    shifts = query.order_by(Shift.date.desc()).all()
    shift_data = []
    for shift in shifts:
        incidents = Incident.query.filter_by(shift_id=shift.id).all()
        key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        # Attach responsible engineer name
        key_points_data = []
        for kp in key_points:
            engineer = TeamMember.query.get(kp.responsible_engineer_id)
            key_points_data.append({
                'description': kp.description,
                'status': kp.status,
                'responsible': engineer.name if engineer else 'N/A'
            })
        shift_data.append({
            'shift': shift,
            'incidents': incidents,
            'key_points': key_points_data
        })
    return render_template(
        'handover_reports.html',
        shift_data=shift_data,
        date_filter=date_filter or '',
        shift_type_filter=shift_type_filter or '',
        accounts=accounts,
        teams=teams,
        selected_account_id=account_id,
        selected_team_id=team_id
    )

