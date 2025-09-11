
from flask import Blueprint, render_template, request, send_file, session
from flask_login import login_required, current_user
from datetime import datetime
from models.models import Shift, Incident, ShiftKeyPoint, TeamMember, Account, Team
from services.export_service import export_incidents_csv, export_keypoints_pdf

from services.audit_service import log_action


reports_bp = Blueprint('reports', __name__)


# Bulk export filtered handover reports as CSV or PDF
@reports_bp.route('/handover-reports/export/bulk', methods=['GET'])
@login_required
def export_handover_bulk():
    log_action('Export Reports', f'Format: {request.args.get("format")}, Filters: account_id={request.args.get("account_id")}, team_id={request.args.get("team_id")}, date={request.args.get("date")}, shift_type={request.args.get("shift_type")}')
    date_filter = request.args.get('date')
    shift_type_filter = request.args.get('shift_type')
    account_id = request.args.get('account_id')
    team_id = request.args.get('team_id')
    format_type = request.args.get('format', 'csv')
    query = Shift.query
    if account_id:
        query = query.filter_by(account_id=account_id)
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
    shifts = query.order_by(Shift.date.desc()).all()
    rows = []
    for shift in shifts:
        incidents = Incident.query.filter_by(shift_id=shift.id).all()
        key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
        incident_titles = '; '.join([f"[{i.type}] {i.title}" for i in incidents])
        keypoint_details = '; '.join([
            f"{kp.description} ({kp.status}) [Responsible: {TeamMember.query.get(kp.responsible_engineer_id).name if kp.responsible_engineer_id else 'N/A'}]"
            for kp in key_points
        ])
        rows.append({
            'Date': shift.date,
            'Current Shift': shift.current_shift_type,
            'Status': shift.status,
            'Incidents': incident_titles,
            'Key Points': keypoint_details
        })
    if format_type == 'csv':
        import pandas as pd, io
        df = pd.DataFrame(rows)
        csv_io = io.StringIO()
        df.to_csv(csv_io, index=False)
        csv_io.seek(0)
        return send_file(io.BytesIO(csv_io.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='handover_reports.csv')
    elif format_type == 'pdf':
        import io
        from reportlab.pdfgen import canvas
        pdf_io = io.BytesIO()
        c = canvas.Canvas(pdf_io)
        c.drawString(100, 800, "Shift Handover Reports")
        y = 780
        for row in rows:
            c.drawString(100, y, f"Date: {row['Date']} | Shift: {row['Current Shift']} | Status: {row['Status']}")
            y -= 20
            c.drawString(120, y, f"Incidents: {row['Incidents']}")
            y -= 20
            c.drawString(120, y, f"Key Points: {row['Key Points']}")
            y -= 30
            if y < 100:
                c.showPage()
                y = 800
        c.save()
        pdf_io.seek(0)
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name='handover_reports.pdf')
    else:
        return "Invalid format", 400


# Export incidents as CSV for a single shift
@reports_bp.route('/handover-reports/export/csv/<int:shift_id>', methods=['GET'])
@login_required
def export_handover_csv(shift_id):
    log_action('Export Single Shift CSV', f'Shift ID: {shift_id}')
    shift = Shift.query.get_or_404(shift_id)
    return export_incidents_csv(shift.date, shift_id)

# Export key points as PDF for a single shift
@reports_bp.route('/handover-reports/export/pdf/<int:shift_id>', methods=['GET'])
@login_required
def export_handover_pdf(shift_id):
    log_action('Export Single Shift PDF', f'Shift ID: {shift_id}')
    shift = Shift.query.get_or_404(shift_id)
    return export_keypoints_pdf(shift.date, shift_id)


@reports_bp.route('/handover-reports', methods=['GET'])
@login_required
def handover_reports():
    log_action('View Reports Tab', f'Filters: account_id={request.args.get("account_id")}, team_id={request.args.get("team_id")}, date={request.args.get("date")}, shift_type={request.args.get("shift_type")}')
    date_filter = request.args.get('date')
    shift_type_filter = request.args.get('shift_type')
    account_id = None
    team_id = None
    accounts = []
    teams = []
    query = Shift.query
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
    shifts = query.order_by(Shift.date.desc()).all()
    shift_data = []
    for shift in shifts:
        incidents = Incident.query.filter_by(shift_id=shift.id).all()
        key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()
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

