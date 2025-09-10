
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask import session
from models.models import TeamMember, Shift, Incident, ShiftKeyPoint, ShiftRoster, current_shift_engineers, next_shift_engineers
from app import db
from services.email_service import send_handover_email
from datetime import datetime, timedelta, time as dt_time
import pytz

handover_bp = Blueprint('handover', __name__)

# API endpoint to fetch engineers for a given date and shift type
@handover_bp.route('/api/get_engineers', methods=['GET'])
@login_required
def get_engineers():
    date_str = request.args.get('date')
    shift_type = request.args.get('shift_type')
    if not date_str or not shift_type:
        return jsonify({'error': 'Missing date or shift_type'}), 400
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
    shift_code = shift_map.get(shift_type)
    if not shift_code:
        return jsonify({'error': 'Invalid shift_type'}), 400
    # Night shift logic
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        date = date - timedelta(days=1)
    query = ShiftRoster.query.filter_by(date=date, shift_code=shift_code)
    if current_user.role != 'admin':
        query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    entries = query.all()
    member_ids = [e.team_member_id for e in entries]
    tm_query = TeamMember.query.filter(TeamMember.id.in_(member_ids))
    if current_user.role != 'admin':
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    engineers = tm_query.all() if member_ids else []
    return jsonify({'engineers': [e.name for e in engineers]})

@handover_bp.route('/handover/drafts')
@login_required
def handover_drafts():
    # Show all drafts (no created_by field in Shift model)
    query = Shift.query.filter_by(status='draft')
    # Use session-based filtering for super/account admin
    if current_user.role == 'super_admin':
        account_id = session.get('selected_account_id')
        team_id = session.get('selected_team_id')
        if account_id:
            query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        team_id = session.get('selected_team_id')
        query = query.filter_by(account_id=account_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
    else:
        query = query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    drafts = query.all()
    return render_template('handover_drafts.html', drafts=drafts)

@handover_bp.route('/handover/edit/<int:shift_id>', methods=['GET', 'POST'])
@login_required
def edit_handover(shift_id):
    if current_user.role == 'viewer':
        flash('You do not have permission to edit handover forms.')
        return redirect(url_for('dashboard.dashboard'))
    shift = Shift.query.get_or_404(shift_id)
    if current_user.role != 'admin' and (shift.account_id != current_user.account_id or shift.team_id != current_user.team_id):
        flash('You do not have permission to edit this handover form.')
        return redirect(url_for('dashboard.dashboard'))
    tm_query = TeamMember.query
    if current_user.role != 'admin':
        tm_query = tm_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
    team_members = tm_query.all()
    # Fetch incidents by type for prepopulation
    open_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Active').all()]
    closed_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Closed').all()]
    priority_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Priority').all()]
    handover_incidents = [i.title for i in Incident.query.filter_by(shift_id=shift.id, type='Handover').all()]

    if request.method == 'POST':
        shift.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        shift.current_shift_type = request.form['current_shift_type']
        shift.next_shift_type = request.form['next_shift_type']
        action = request.form.get('action', 'send')
        shift.status = 'draft' if action == 'save' else 'sent'
        # Clear and update engineers
        shift.current_engineers.clear()
        shift.next_engineers.clear()
        # (Re)populate engineers as in create
        shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
        current_shift_code = shift_map[shift.current_shift_type]
        next_shift_code = shift_map[shift.next_shift_type]
        ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
        def get_engineers_for_shift(date, shift_code):
            entries = ShiftRoster.query.filter_by(date=date, shift_code=shift_code).all()
            member_ids = [e.team_member_id for e in entries]
            return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
        if shift.current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
            night_date = shift.date - timedelta(days=1)
            current_engineers_objs = get_engineers_for_shift(night_date, current_shift_code)
        else:
            current_engineers_objs = get_engineers_for_shift(shift.date, current_shift_code)
        if shift.next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
            next_date = shift.date + timedelta(days=1)
            next_engineers_objs = get_engineers_for_shift(next_date, next_shift_code)
        else:
            next_engineers_objs = get_engineers_for_shift(shift.date, next_shift_code)
        for member in current_engineers_objs:
            shift.current_engineers.append(member)
        for member in next_engineers_objs:
            shift.next_engineers.append(member)
        # Remove and re-add incidents/keypoints
        Incident.query.filter_by(shift_id=shift.id).delete()
        ShiftKeyPoint.query.filter_by(shift_id=shift.id).delete()
        db.session.commit()
        def add_incident(field, inc_type):
            vals = request.form.getlist(field)
            for val in vals:
                if val.strip():
                    incident = Incident(
                        title=val,
                        status=inc_type if inc_type in ['Active','Closed'] else '',
                        priority='High' if inc_type=='Priority' else '',
                        handover=val if inc_type=='Handover' else '',
                        shift_id=shift.id,
                        type=inc_type,
                        account_id=shift.account_id,
                        team_id=shift.team_id
                    )
                    db.session.add(incident)
        add_incident('open_incidents', 'Active')
        add_incident('closed_incidents', 'Closed')
        add_incident('priority_incidents', 'Priority')
        add_incident('handover_incidents', 'Handover')
        key_point_numbers = request.form.getlist('key_point_number')
        key_point_details = request.form.getlist('key_point_details')
        jira_ids = request.form.getlist('jira_id')
        responsible_persons = request.form.getlist('responsible_person')
        key_point_statuses = request.form.getlist('key_point_status')
        for i in range(len(key_point_numbers)):
            details = key_point_details[i].strip() if i < len(key_point_details) else ''
            jira_id = jira_ids[i].strip() if i < len(jira_ids) else ''
            responsible_id = responsible_persons[i] if i < len(responsible_persons) else ''
            status = key_point_statuses[i] if i < len(key_point_statuses) else 'Open'
            if details:
                # If status is being set to Closed, close all previous open/in-progress key points with same description and jira_id
                if status == 'Closed':
                    prev_kps = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.description == details,
                        ShiftKeyPoint.jira_id == (jira_id if jira_id else None),
                        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                    ).all()
                    for pkp in prev_kps:
                        pkp.status = 'Closed'
                        db.session.add(pkp)
                    # Do not add a new key point for closed status
                    continue
                # Try to find all existing open/in-progress key points with the same description and jira_id
                existing_kps = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.description == details,
                    ShiftKeyPoint.jira_id == (jira_id if jira_id else None),
                    ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                ).all()
                if existing_kps:
                    for existing_kp in existing_kps:
                        existing_kp.shift_id = shift.id
                        existing_kp.responsible_engineer_id = int(responsible_id) if responsible_id else None
                        existing_kp.status = status
                        existing_kp.account_id = shift.account_id
                        existing_kp.team_id = shift.team_id
                        db.session.add(existing_kp)
                else:
                    kp = ShiftKeyPoint(
                        description=details,
                        status=status,
                        responsible_engineer_id=int(responsible_id) if responsible_id else None,
                        shift_id=shift.id,
                        jira_id=jira_id if jira_id else None,
                        account_id=shift.account_id,
                        team_id=shift.team_id
                    )
                    db.session.add(kp)
        db.session.commit()
        if action == 'send':
            import logging
            logging.basicConfig(level=logging.DEBUG)
            logging.debug(f"[EMAIL] Attempting to send handover email for shift_id={shift.id}, date={shift.date}, current_shift_type={shift.current_shift_type}, next_shift_type={shift.next_shift_type}")
            try:
                send_handover_email(shift)
                logging.debug(f"[EMAIL] Email sent successfully for shift_id={shift.id}")
                flash('Handover submitted and email sent!')
            except Exception as e:
                logging.error(f"[EMAIL] Failed to send email for shift_id={shift.id}: {e}")
                flash(f'Error sending email: {e}')
        else:
            flash('Draft updated.')
        # After save or send, redirect to drafts (for save) or reports (for send)
        if action == 'save':
            return redirect(url_for('reports.handover_reports'))
        else:
            return redirect(url_for('reports.handover_reports'))
    # GET: populate form with existing data
    current_engineers = [m.name for m in shift.current_engineers]
    next_engineers = [m.name for m in shift.next_engineers]
    # Deduplicate open key points for this shift by (description, jira_id), only non-Closed
    all_kps = [kp for kp in ShiftKeyPoint.query.filter_by(shift_id=shift.id).all() if kp.status in ('Open', 'In Progress')]
    kp_map = {}
    for kp in all_kps:
        key = (kp.description, kp.jira_id)
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    open_key_points = list(kp_map.values())
    return render_template('handover_form.html',
        team_members=team_members,
        current_engineers=current_engineers,
        next_engineers=next_engineers,
        current_shift_type=shift.current_shift_type,
        next_shift_type=shift.next_shift_type,
        open_key_points=open_key_points,
        shift=shift,
        open_incidents=open_incidents,
        closed_incidents=closed_incidents,
        priority_incidents=priority_incidents,
        handover_incidents=handover_incidents
    )




@handover_bp.route('/handover', methods=['GET', 'POST'])
@login_required
def handover():
    # Get selected account/team for Super Admin
    account_id = request.form.get('account_id') if current_user.role == 'super_admin' else current_user.account_id
    team_id_raw = request.form.get('team_id') if current_user.role in ['super_admin', 'account_admin'] else current_user.team_id
    try:
        team_id = int(team_id_raw) if team_id_raw not in (None, '', 'None') else None
    except (TypeError, ValueError):
        team_id = None
    # Validate team_id exists
    from models.models import Team
    valid_team = Team.query.get(team_id) if team_id else None
    if request.method == 'POST' and not valid_team:
        flash('Please select a valid Team before submitting the handover.')
        return redirect(url_for('handover.handover'))
    # If GET and no valid team, show form with error and disable submit
    show_team_error = not valid_team
    from models.models import Team
    if current_user.role == 'super_admin':
        teams = Team.query.filter_by(status='active').all()
    elif current_user.role == 'account_admin':
        teams = Team.query.filter_by(account_id=current_user.account_id, status='active').all()
    else:
        teams = Team.query.filter_by(account_id=current_user.account_id, id=current_user.team_id, status='active').all()
    team_members = TeamMember.query.filter_by(account_id=account_id, team_id=team_id).all() if account_id and team_id else []
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    default_date = ist_now.date()
    shift_map = {'Morning': 'D', 'Evening': 'E', 'Night': 'N'}
    # POST: Save as draft or send
    if request.method == 'POST':
        # Get form data
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        current_shift_type = request.form['current_shift_type']
        next_shift_type = request.form['next_shift_type']
        action = request.form.get('action', 'send')
        # Create new Shift record
        shift = Shift(
            date=date,
            current_shift_type=current_shift_type,
            next_shift_type=next_shift_type,
            status='draft' if action == 'save' else 'sent',
            account_id=account_id,
            team_id=team_id
        )
        db.session.add(shift)
        db.session.commit()
        # Populate engineers
        current_shift_code = shift_map[current_shift_type]
        next_shift_code = shift_map[next_shift_type]
        def get_engineers_for_shift(date, shift_code):
            entries = ShiftRoster.query.filter_by(date=date, shift_code=shift_code).all()
            member_ids = [e.team_member_id for e in entries]
            return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
        if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
            night_date = date - timedelta(days=1)
            current_engineers_objs = get_engineers_for_shift(night_date, current_shift_code)
        else:
            current_engineers_objs = get_engineers_for_shift(date, current_shift_code)
        if next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
            next_date = date + timedelta(days=1)
            next_engineers_objs = get_engineers_for_shift(next_date, next_shift_code)
        else:
            next_engineers_objs = get_engineers_for_shift(date, next_shift_code)
        for member in current_engineers_objs:
            shift.current_engineers.append(member)
        for member in next_engineers_objs:
            shift.next_engineers.append(member)
        # Add incidents
        def add_incident(field, inc_type):
            vals = request.form.getlist(field)
            for val in vals:
                if val.strip():
                    incident = Incident(
                        title=val,
                        status=inc_type if inc_type in ['Active','Closed'] else '',
                        priority='High' if inc_type=='Priority' else '',
                        handover=val if inc_type=='Handover' else '',
                        shift_id=shift.id,
                        type=inc_type,
                        account_id=account_id,
                        team_id=team_id
                    )
                    db.session.add(incident)
        add_incident('open_incidents', 'Active')
        add_incident('closed_incidents', 'Closed')
        add_incident('priority_incidents', 'Priority')
        add_incident('handover_incidents', 'Handover')
        # Add key points
        key_point_numbers = request.form.getlist('key_point_number')
        key_point_details = request.form.getlist('key_point_details')
        jira_ids = request.form.getlist('jira_id')
        responsible_persons = request.form.getlist('responsible_person')
        key_point_statuses = request.form.getlist('key_point_status')
        for i in range(len(key_point_numbers)):
            details = key_point_details[i].strip() if i < len(key_point_details) else ''
            jira_id = jira_ids[i].strip() if i < len(jira_ids) else ''
            responsible_id = responsible_persons[i] if i < len(responsible_persons) else ''
            status = key_point_statuses[i] if i < len(key_point_statuses) else 'Open'
            if details:
                # If status is being set to Closed, close all previous open/in-progress key points with same description and jira_id
                if status == 'Closed':
                    prev_kps = ShiftKeyPoint.query.filter(
                        ShiftKeyPoint.description == details,
                        ShiftKeyPoint.jira_id == (jira_id if jira_id else None),
                        ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                    ).all()
                    for pkp in prev_kps:
                        pkp.status = 'Closed'
                        db.session.add(pkp)
                    # Do not add a new key point for closed status
                    continue
                # Try to find all existing open/in-progress key points with the same description and jira_id
                existing_kps = ShiftKeyPoint.query.filter(
                    ShiftKeyPoint.description == details,
                    ShiftKeyPoint.jira_id == (jira_id if jira_id else None),
                    ShiftKeyPoint.status.in_(['Open', 'In Progress'])
                ).all()
                if existing_kps:
                    for existing_kp in existing_kps:
                        existing_kp.shift_id = shift.id
                        existing_kp.responsible_engineer_id = int(responsible_id) if responsible_id else None
                        existing_kp.status = status
                        existing_kp.account_id = account_id
                        existing_kp.team_id = team_id
                        db.session.add(existing_kp)
                else:
                    kp = ShiftKeyPoint(
                        description=details,
                        status=status,
                        responsible_engineer_id=int(responsible_id) if responsible_id else None,
                        shift_id=shift.id,
                        jira_id=jira_id if jira_id else None,
                        account_id=account_id,
                        team_id=team_id
                    )
                    db.session.add(kp)
        db.session.commit()
        if action == 'send':
            import logging
            logging.basicConfig(level=logging.DEBUG)
            logging.debug(f"[EMAIL] Attempting to send handover email for shift_id={shift.id}, date={shift.date}, current_shift_type={shift.current_shift_type}, next_shift_type={shift.next_shift_type}")
            try:
                send_handover_email(shift)
                logging.debug(f"[EMAIL] Email sent successfully for shift_id={shift.id}")
                flash('Handover submitted and email sent!')
            except Exception as e:
                logging.error(f"[EMAIL] Failed to send email for shift_id={shift.id}: {e}")
                flash(f'Error sending email: {e}')
        else:
            flash('Draft saved.')
        return redirect(url_for('reports.handover_reports'))
    # GET: render form with defaults
    # Determine current and next shift based on time
    hour = ist_now.hour
    minute = ist_now.minute
    if dt_time(6,45) <= ist_now.time() < dt_time(14,45):
        current_shift_type = 'Morning'
        next_shift_type = 'Evening'
    elif dt_time(14,45) <= ist_now.time() < dt_time(21,45):
        current_shift_type = 'Evening'
        next_shift_type = 'Night'
    else:
        current_shift_type = 'Night'
        next_shift_type = 'Morning'
    def get_engineers_for_shift(date, shift_code):
        entries = ShiftRoster.query.filter_by(date=date, shift_code=shift_code).all()
        member_ids = [e.team_member_id for e in entries]
        return TeamMember.query.filter(TeamMember.id.in_(member_ids)).all() if member_ids else []
    if current_shift_type == 'Night' and ist_now.time() < dt_time(6,45):
        night_date = default_date - timedelta(days=1)
        current_engineers_objs = get_engineers_for_shift(night_date, shift_map[current_shift_type])
    else:
        current_engineers_objs = get_engineers_for_shift(default_date, shift_map[current_shift_type])
    if next_shift_type == 'Night' and ist_now.time() >= dt_time(21,45):
        next_date = default_date + timedelta(days=1)
        next_engineers_objs = get_engineers_for_shift(next_date, shift_map[next_shift_type])
    else:
        next_engineers_objs = get_engineers_for_shift(default_date, shift_map[next_shift_type])
    current_engineers = [m.name for m in current_engineers_objs]
    next_engineers = [m.name for m in next_engineers_objs]
    # Carry forward all open/in-progress key points from all previous and current 'sent' shifts (date <= today), deduplicated by (description, jira_id), and only non-Closed
    prev_shifts = Shift.query.filter(Shift.date <= default_date, Shift.status == 'sent').all()
    all_prev_kps = []
    for prev_shift in prev_shifts:
        all_prev_kps.extend([
            kp for kp in ShiftKeyPoint.query.filter_by(shift_id=prev_shift.id).all() if kp.status in ('Open', 'In Progress')
        ])
    # Deduplicate: keep only the latest (by id) for each (description, jira_id) pair, and only if not Closed
    kp_map = {}
    for kp in all_prev_kps:
        if kp.status == 'Closed':
            continue
        key = (kp.description, kp.jira_id)
        if key not in kp_map or kp.id > kp_map[key].id:
            kp_map[key] = kp
    open_key_points = list(kp_map.values())
    # Always show at least one blank row for new key point entry in the form
    return render_template('handover_form.html',
        team_members=team_members,
        teams=teams,
        current_engineers=current_engineers,
        next_engineers=next_engineers,
        current_shift_type=current_shift_type,
        next_shift_type=next_shift_type,
        open_key_points=open_key_points,
        shift=None,
        open_incidents=[],
        closed_incidents=[],
        priority_incidents=[],
        handover_incidents=[],
        today=default_date.strftime('%Y-%m-%d'),
        show_team_error=show_team_error
    )

