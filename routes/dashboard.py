
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
    current_engineers = get_engineers_for_shift(today, current_shift_code)
    next_shift_engineers = get_engineers_for_shift(next_date, next_shift_code)
    open_key_points = ShiftKeyPoint.query.filter_by(account_id=filter_account_id, team_id=filter_team_id, status='Open').all()

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
        next_date=next_date
    )
    print(f"[DEBUG] Dashboard: next_engineers={[e.name for e in next_engineers]}")
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
    else:  # default 7d
        from_date = today - timedelta(days=7)
        to_date = today

    # Summary counts for chart
    base_incident_query = db.session.query(Incident).join(Shift, Incident.shift_id == Shift.id)
    if current_user.role != 'admin':
        base_incident_query = base_incident_query.filter(Incident.account_id==current_user.account_id, Incident.team_id==current_user.team_id)
    open_count = base_incident_query.filter(Incident.status=='Active', Incident.type=='Active', Shift.date >= from_date, Shift.date <= to_date).count()
    closed_count = base_incident_query.filter(Incident.status=='Closed', Incident.type=='Closed', Shift.date >= from_date, Shift.date <= to_date).count()
    priority_count = base_incident_query.filter(Incident.type=='Priority', Shift.date >= from_date, Shift.date <= to_date).count()

    # Show only open incidents from the most recent handover form (latest shift)
    shift_query = db.session.query(Shift)
    if current_user.role != 'admin':
        shift_query = shift_query.filter(Shift.account_id==current_user.account_id, Shift.team_id==current_user.team_id)
    latest_shift = shift_query.order_by(Shift.date.desc(), Shift.id.desc()).first()
    open_incidents = []
    if latest_shift:
        inc_query = db.session.query(Incident).filter(
            Incident.shift_id == latest_shift.id,
            Incident.status == 'Active',
            Incident.type == 'Active'
        )
        if current_user.role != 'admin':
            inc_query = inc_query.filter(Incident.account_id==current_user.account_id, Incident.team_id==current_user.team_id)
        open_incidents = inc_query.all()

    # Deduplicate open key points by description and jira_id (show only latest per pair), only non-Closed
    kp_query = db.session.query(
        ShiftKeyPoint.description,
        ShiftKeyPoint.jira_id,
        db.func.max(ShiftKeyPoint.id).label('max_id')
    ).filter(ShiftKeyPoint.status.in_(['Open', 'In Progress']))
    if current_user.role != 'admin':
        kp_query = kp_query.filter(ShiftKeyPoint.account_id==current_user.account_id, ShiftKeyPoint.team_id==current_user.team_id)
    kp_subq = kp_query.group_by(ShiftKeyPoint.description, ShiftKeyPoint.jira_id).subquery()
    open_key_points_query = db.session.query(ShiftKeyPoint).join(
        kp_subq, ShiftKeyPoint.id == kp_subq.c.max_id
    ).filter(ShiftKeyPoint.status.in_(['Open', 'In Progress']))
    if current_user.role != 'admin':
        open_key_points_query = open_key_points_query.filter(ShiftKeyPoint.account_id==current_user.account_id, ShiftKeyPoint.team_id==current_user.team_id)
    open_key_points = open_key_points_query.all()
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
    current_shift_type, next_shift_type = get_shift_type_and_next(ist_now)
    current_shift_code = shift_map[current_shift_type]
    next_shift_code = shift_map[next_shift_type]
    # For night shift, if after midnight, use previous day's date for roster
    if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        night_date = today - timedelta(days=1)
        current_engineers = get_engineers_for_shift(night_date, current_shift_code)
    else:
        current_engineers = get_engineers_for_shift(today, current_shift_code)
    # Next shift engineers: always use tomorrow's date for next shift
    next_date = today + timedelta(days=1)
    next_engineers = get_engineers_for_shift(next_date, next_shift_code)

    # Date-wise chart data
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
        open_incidents=open_incidents,
        current_engineers=current_engineers,
        next_shift_engineers=next_engineers,
        graphJSON=graphJSON,
        open_key_points=open_key_points,
        selected_range=range_opt,
        start_date=start_date or from_date.strftime('%Y-%m-%d'),
        end_date=end_date or to_date.strftime('%Y-%m-%d')
    )
