from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask import session
from models.models import TeamMember, ShiftRoster
from app import db
from datetime import datetime

roster_bp = Blueprint('roster', __name__)



# Shift Roster View with Month/Year filters
@roster_bp.route('/roster', methods=['GET', 'POST'])
@login_required
def roster():
    if request.method == 'POST' and current_user.role == 'viewer':
        flash('You do not have permission to edit shift roster.')
        return redirect(url_for('roster.roster'))
    # Get filter values from query params
    import calendar
    month_str = request.args.get('month')
    year = request.args.get('year', default=None, type=int)
    now = datetime.now()
    month = None
    if month_str:
        try:
            month = list(calendar.month_name).index(month_str)
        except ValueError:
            month = None
    if not month:
        month = now.month
    if not year:
        year = now.year
    filter_date = request.args.get('filter_date')
    filter_shift = request.args.get('filter_shift')
    from models.models import Account, Team
    query = db.session.query(ShiftRoster)
    account_id = None
    team_id = None
    accounts = []
    teams = []
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id')
        team_id = request.args.get('team_id')
        # Update session with selected values for consistent filtering
        if account_id:
            session['selected_account_id'] = account_id
        else:
            account_id = session.get('selected_account_id')
        if team_id:
            try:
                team_id = int(team_id)
                session['selected_team_id'] = team_id
            except (TypeError, ValueError):
                team_id = None
        else:
            team_id = session.get('selected_team_id')
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        if account_id:
            query = query.filter(ShiftRoster.account_id==account_id)
        if team_id:
            query = query.filter(ShiftRoster.team_id==team_id)
        # Ensure team_id is int for team_members query as well
        tm_query = TeamMember.query
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id') or session.get('selected_team_id')
        # Ensure team_id is int if present
        if team_id:
            try:
                team_id = int(team_id)
            except (TypeError, ValueError):
                team_id = None
        query = query.filter(ShiftRoster.account_id==account_id)
        if team_id:
            query = query.filter(ShiftRoster.team_id==team_id)
        else:
            # If no team selected, show all teams for account
            team_ids = [t.id for t in teams]
            query = query.filter(ShiftRoster.team_id.in_(team_ids))
    else:
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
        query = query.filter(ShiftRoster.account_id==account_id)
        query = query.filter(ShiftRoster.team_id==team_id)
    # Removed debug flash
    if month:
        query = query.filter(db.extract('month', ShiftRoster.date) == month)
    if year:
        query = query.filter(db.extract('year', ShiftRoster.date) == year)
    roster_entries = query.order_by(ShiftRoster.date).all()
    if not roster_entries:
        pass
    tm_query = TeamMember.query
    if current_user.role == 'super_admin':
        account_id = session.get('selected_account_id')
        team_id = session.get('selected_team_id')
        if account_id:
            tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        team_id = request.args.get('team_id') or session.get('selected_team_id')
        if team_id:
            try:
                team_id = int(team_id)
            except (TypeError, ValueError):
                team_id = None
        tm_query = tm_query.filter_by(account_id=account_id)
        if team_id:
            tm_query = tm_query.filter_by(team_id=team_id)
        else:
            # If no team selected, show all team members for account
            team_ids = [t.id for t in teams]
            tm_query = tm_query.filter(TeamMember.team_id.in_(team_ids))
    else:
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    all_members_all = tm_query.all()
    # Only include members with at least one shift entry
    member_ids_with_shifts = {entry.team_member_id for entry in roster_entries}
    all_members = [m for m in all_members_all if m.id in member_ids_with_shifts]
    # Debug: Show roster_entries and all_members
    # Removed debug flash
    # Build a set of all dates in the filtered result
    all_dates = sorted({entry.date for entry in roster_entries})
    # Build roster data: {member_name: {date: shift_code}}
    roster_data = {member.name: {date: '' for date in all_dates} for member in all_members}
    for entry in roster_entries:
        member = next((m for m in all_members if m.id == entry.team_member_id), None)
        if member:
            roster_data[member.name][entry.date] = entry.shift_code
    # For dropdowns
    months = [calendar.month_name[i] for i in range(1, 13)]
    # Show current year and next 10 years
    current_year = now.year
    years = [current_year + i for i in range(11)]

    # Additional filter: present team members for selected date and shift
    present_members = []
    present_members_by_shift = {}
    if filter_date:
        date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        if filter_shift is not None and filter_shift != '':
            present_entries = ShiftRoster.query.filter(ShiftRoster.date == date_obj, ShiftRoster.shift_code == filter_shift).all()
            present_member_ids = [e.team_member_id for e in present_entries]
            present_members = TeamMember.query.filter(TeamMember.id.in_(present_member_ids)).all() if present_member_ids else []
        else:
            # Group by shift_code, including LE (Late Evening) and G (General)
            shift_codes = ['D', 'E', 'N', 'LE', 'G']
            for code in shift_codes:
                entries = ShiftRoster.query.filter(ShiftRoster.date == date_obj, ShiftRoster.shift_code == code).all()
                member_ids = [e.team_member_id for e in entries]
                members = TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
                present_members_by_shift[code] = members
            # Ensure all shift codes are present in the dict, even if empty
            for code in shift_codes:
                if code not in present_members_by_shift:
                    present_members_by_shift[code] = []

    return render_template(
        'shift_roster.html',
        all_dates=all_dates,
        all_members=all_members,
        roster_data=roster_data,
        months=months,
        years=years,
        selected_month=month,
        selected_year=year,
        filter_date=filter_date,
        filter_shift=filter_shift,
        present_members=present_members,
        present_members_by_shift=present_members_by_shift if 'present_members_by_shift' in locals() else {}
    )

