
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models.models import Incident, TeamMember, ShiftRoster, ShiftKeyPoint, Shift, Account, Team, User
from app import db
import plotly.graph_objs as go
import plotly
import json
from datetime import datetime, timedelta, time as dt_time
import pytz

dashboard_bp = Blueprint('dashboard', __name__)

def get_ist_now():
    utc_now = datetime.utcnow()
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

def get_shift_type_and_next(now):
    # Shift timings (IST):
    # Morning: 6:30-15:30, Evening: 14:45-23:45, Night: 21:45-6:45 (next day)
    t = now.time()
    if dt_time(6,30) <= t < dt_time(15,30):
        return 'Morning', 'Evening'
    elif dt_time(14,45) <= t < dt_time(23,45):
        return 'Evening', 'Night'
    else:
        # Night shift covers 21:45-6:45 (next day)
        return 'Night', 'Morning'

def get_engineers_for_shift(date, shift_code):
    # shift_code: 'E' (Evening), 'D' (Day/Morning), 'N' (Night)
    query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
    if not current_user.is_authenticated or current_user.role != 'admin':
        query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    entries = query.all()
    member_ids = [e.team_member_id for e in entries]
    tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids))
    if not current_user.is_authenticated or current_user.role != 'admin':
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    return tm_query.all() if member_ids else []

@dashboard_bp.route('/')
@login_required
def dashboard():
    ist_now = get_ist_now()
    today = ist_now.date()
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
    current_shift_type, next_shift_type = get_shift_type_and_next(ist_now)
    current_shift_code = shift_map[current_shift_type]
    next_shift_code = shift_map[next_shift_type]
    next_date = today + timedelta(days=1)

    from flask import session
    print(f"[DEBUG] Dashboard: current_user.is_authenticated={getattr(current_user, 'is_authenticated', None)}, id={getattr(current_user, 'id', None)}, username={getattr(current_user, 'username', None)}")
    accounts = []
    teams = []
    selected_account_id = None
    selected_team_id = None
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        selected_account_id = request.args.get('account_id') or session.get('selected_account_id')
        teams = Team.query.filter_by(is_active=True)
        if selected_account_id:
            teams = teams.filter_by(account_id=selected_account_id)
        teams = teams.all()
        selected_team_id = request.args.get('team_id') or session.get('selected_team_id')
        filter_account_id = selected_account_id
        filter_team_id = selected_team_id
    elif current_user.role == 'account_admin':
        filter_account_id = current_user.account_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        teams = Team.query.filter_by(account_id=filter_account_id, is_active=True).all()
        selected_team_id = request.args.get('team_id') or session.get('selected_team_id')
        filter_team_id = selected_team_id if selected_team_id else (teams[0].id if teams else None)
    else:
        filter_account_id = current_user.account_id
        filter_team_id = current_user.team_id
        accounts = [Account.query.get(filter_account_id)] if filter_account_id else []
        teams = [Team.query.get(filter_team_id)] if filter_team_id else []

    # Filter data by account/team
    open_incidents = Incident.query.filter_by(account_id=filter_account_id, team_id=filter_team_id, status='Active').all()
    # Use handover form logic for fetching engineers
    def get_engineers_for_shift(date, shift_code):
        entries = ShiftRoster.query.filter_by(date=date, shift_code=shift_code, account_id=filter_account_id, team_id=filter_team_id).all()
        member_ids = [e.team_member_id for e in entries]
        return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []

    ist_now = get_ist_now()
    # Current shift engineers
    if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        night_date = today - timedelta(days=1)
        current_engineers = get_engineers_for_shift(night_date, current_shift_code)
    else:
        current_engineers = get_engineers_for_shift(today, current_shift_code)
    # Next shift engineers
    if next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
        next_date_for_engineers = today + timedelta(days=1)
        next_shift_engineers = get_engineers_for_shift(next_date_for_engineers, next_shift_code)
    else:
        next_shift_engineers = get_engineers_for_shift(today, next_shift_code)
    open_key_points = ShiftKeyPoint.query.filter_by(account_id=filter_account_id, team_id=filter_team_id, status='Open').all()

    # Chart logic
    range_opt = request.args.get('range', '7d')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if range_opt == '1d':
        from_date = today - timedelta(days=1)
        to_date = today
    elif range_opt == '7d':
        from_date = today - timedelta(days=7)
        to_date = today
    elif range_opt == '30d':
        from_date = today - timedelta(days=30)
        to_date = today
    elif range_opt == '1y':
        from_date = today - timedelta(days=365)
        to_date = today
    elif range_opt == 'custom' and start_date and end_date:
        from_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        to_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        from_date = today - timedelta(days=7)
        to_date = today

    date_list = [(from_date + timedelta(days=i)) for i in range((to_date - from_date).days + 1)]
    open_counts = []
    closed_counts = []
    handover_counts = []
    priority_counts = []
    for d in date_list:
        base_incident_query = db.session.query(Incident).join(Shift, Incident.shift_id == Shift.id)
        if current_user.role != 'admin':
            base_incident_query = base_incident_query.filter(Incident.account_id==current_user.account_id, Incident.team_id==current_user.team_id)
        open_c = base_incident_query.filter(Incident.status=='Active', Incident.type=='Active', Shift.date==d).count()
        closed_c = base_incident_query.filter(Incident.status=='Closed', Incident.type=='Closed', Shift.date==d).count()
        handover_c = base_incident_query.filter(Incident.type=='Handover', Shift.date==d).count()
        priority_c = base_incident_query.filter(Incident.type=='Priority', Shift.date==d).count()
        open_counts.append(open_c)
        closed_counts.append(closed_c)
        handover_counts.append(handover_c)
        priority_counts.append(priority_c)

    x_dates = [d.strftime('%Y-%m-%d') for d in date_list]
    trace_open = go.Bar(x=x_dates, y=open_counts, name='Open Incidents')
    trace_closed = go.Bar(x=x_dates, y=closed_counts, name='Closed Incidents')
    trace_handover = go.Bar(x=x_dates, y=handover_counts, name='Handover Incidents')
    trace_priority = go.Bar(x=x_dates, y=priority_counts, name='Priority Incidents')
    data = [trace_open, trace_closed, trace_handover, trace_priority]
    layout = go.Layout(barmode='group', xaxis={'title': 'Date'}, yaxis={'title': 'Count'}, title='Incidents by Date')
    graphJSON = json.dumps({'data': data, 'layout': layout}, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        'dashboard.html',
        accounts=accounts,
        teams=teams,
        selected_account_id=filter_account_id,
        selected_team_id=filter_team_id,
        open_incidents=open_incidents,
        current_engineers=current_engineers,
        next_shift_engineers=next_shift_engineers,
        open_key_points=open_key_points,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        today=today,
        next_date=next_date,
        graphJSON=graphJSON,
        selected_range=range_opt,
        start_date=start_date or from_date.strftime('%Y-%m-%d'),
        end_date=end_date or to_date.strftime('%Y-%m-%d')
    )
