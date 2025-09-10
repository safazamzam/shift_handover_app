from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
import os
import pandas as pd

UPLOAD_FOLDER = 'uploads/escalation_matrix'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

escalation_bp = Blueprint('escalation_matrix', __name__)

@escalation_bp.route('/escalation-matrix', methods=['GET', 'POST'])
@login_required
def escalation_matrix():
    app_names = []
    matrix_data = None
    selected_app = request.args.get('application')
    if request.method == 'POST':
        if current_user.role == 'viewer':
            flash('You do not have permission to upload escalation matrix.')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        file = request.files.get('file')
        # Always use current user's account/team for upload mapping
        account_id = getattr(current_user, 'account_id', None)
        team_id = getattr(current_user, 'team_id', None)
        try:
            account_id = int(account_id) if account_id else None
        except Exception:
            account_id = None
        try:
            team_id = int(team_id) if team_id else None
        except Exception:
            team_id = None
        if file and file.filename.endswith('.xlsx'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            # If file exists, remove it before saving new one
            if os.path.exists(filepath):
                os.remove(filepath)
            file.save(filepath)
            # Save or update file info in EscalationMatrixFile table
            from models.models import EscalationMatrixFile, db
            import datetime
            # Find by filename, account_id, and team_id to avoid duplicates
            existing_file = EscalationMatrixFile.query.filter_by(filename=file.filename, account_id=account_id, team_id=team_id).first()
            if existing_file:
                existing_file.upload_time = datetime.datetime.now()
            else:
                matrix_file = EscalationMatrixFile(filename=file.filename, upload_time=datetime.datetime.now(), account_id=account_id, team_id=team_id)
                db.session.add(matrix_file)
            # Parse and save each sheet/row if you have a model for escalation matrix rows
            xls = pd.ExcelFile(filepath)
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)
                table_data = df.where(pd.notnull(df), '').to_dict(orient='records')
                # If you have a model like EscalationMatrixRow, save each row
                # from models.models import EscalationMatrixRow
                # for row in table_data:
                #     escalation_row = EscalationMatrixRow(...)
                #     db.session.add(escalation_row)
            db.session.commit()
            flash('Escalation matrix uploaded and replaced successfully!')
            return redirect(url_for('escalation_matrix.escalation_matrix'))
        else:
            flash('Please upload a valid .xlsx file.')
    # Find the latest uploaded file
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.xlsx')]
    app_names = []
    xls = None
    account_name = None
    team_name = None
    account_id = request.args.get('account_id') or (session.get('selected_account_id') if hasattr(session, 'get') else None)
    team_id = request.args.get('team_id') or (session.get('selected_team_id') if hasattr(session, 'get') else None)
    # Ensure IDs are integers for filtering
    try:
        account_id = int(account_id) if account_id else None
    except Exception:
        account_id = None
    try:
        team_id = int(team_id) if team_id else None
    except Exception:
        team_id = None
    if files:
        from models.models import EscalationMatrixFile, Account, Team
        # Find the latest file for the selected account/team
        file_query = EscalationMatrixFile.query
        # Super Admin: use filter, fallback to latest file if no filter
        if current_user.role == 'super_admin':
            if account_id is not None:
                file_query = file_query.filter_by(account_id=account_id)
            if team_id is not None:
                file_query = file_query.filter_by(team_id=team_id)
            latest_db_file = file_query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if not latest_db_file:
                latest_db_file = EscalationMatrixFile.query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if latest_db_file:
                latest_file = latest_db_file.filename
                xls = pd.ExcelFile(os.path.join(UPLOAD_FOLDER, latest_file))
                # Always use account_id/team_id from the file record for name lookup
                file_account_id = latest_db_file.account_id
                file_team_id = latest_db_file.team_id
                account_obj = Account.query.get(file_account_id) if file_account_id else None
                team_obj = Team.query.get(file_team_id) if file_team_id else None
                account_name = account_obj.name if account_obj else None
                team_name = team_obj.name if team_obj else None
                all_sheets = xls.sheet_names
                # If both account and team names are present, filter by both
                if account_name and team_name:
                    filtered = [s for s in all_sheets if account_name in s and team_name in s]
                    app_names = filtered if filtered else all_sheets
                elif account_name:
                    filtered = [s for s in all_sheets if account_name in s]
                    app_names = filtered if filtered else all_sheets
                elif team_name:
                    filtered = [s for s in all_sheets if team_name in s]
                    app_names = filtered if filtered else all_sheets
                else:
                    app_names = all_sheets
            else:
                app_names = []
        # Account Admin: use user's account, filter by team if selected
        elif current_user.role == 'account_admin':
            file_query = file_query.filter_by(account_id=current_user.account_id)
            if team_id is not None:
                file_query = file_query.filter_by(team_id=team_id)
            latest_db_file = file_query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if not latest_db_file:
                latest_db_file = EscalationMatrixFile.query.filter_by(account_id=current_user.account_id).order_by(EscalationMatrixFile.upload_time.desc()).first()
            if latest_db_file:
                latest_file = latest_db_file.filename
                xls = pd.ExcelFile(os.path.join(UPLOAD_FOLDER, latest_file))
                file_team_id = latest_db_file.team_id
                team_obj = Team.query.get(file_team_id) if file_team_id else None
                team_name = team_obj.name if team_obj else None
                all_sheets = xls.sheet_names
                if team_name:
                    filtered = [s for s in all_sheets if team_name in s]
                    app_names = filtered if filtered else all_sheets
                else:
                    app_names = all_sheets
            else:
                app_names = []
        # Team Admin: use user's account/team
        else:
            file_query = file_query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id)
            latest_db_file = file_query.order_by(EscalationMatrixFile.upload_time.desc()).first()
            if not latest_db_file:
                # Fallback: get latest file for user's account/team
                latest_db_file = EscalationMatrixFile.query.filter_by(account_id=current_user.account_id, team_id=current_user.team_id).order_by(EscalationMatrixFile.upload_time.desc()).first()
            if not latest_db_file:
                # Fallback: get any file for user's account
                latest_db_file = EscalationMatrixFile.query.filter_by(account_id=current_user.account_id).order_by(EscalationMatrixFile.upload_time.desc()).first()
            if latest_db_file:
                latest_file = latest_db_file.filename
                xls = pd.ExcelFile(os.path.join(UPLOAD_FOLDER, latest_file))
                file_team_id = latest_db_file.team_id
                team_obj = Team.query.get(file_team_id) if file_team_id else None
                team_name = team_obj.name if team_obj else None
                all_sheets = xls.sheet_names
                if team_name:
                    filtered = [s for s in all_sheets if team_name in s]
                    app_names = filtered if filtered else all_sheets
                else:
                    app_names = all_sheets
            else:
                app_names = []
    if selected_app and selected_app in app_names:
        df = xls.parse(selected_app)
        matrix_data = df.where(pd.notnull(df), '').to_dict(orient='records')
    from models.models import Account, Team
    accounts = []
    teams = []
    account_id = None
    team_id = None
    selected_team_id = None
    if current_user.role == 'super_admin':
        accounts = Account.query.filter_by(is_active=True).all()
        account_id = request.args.get('account_id') or (session.get('selected_account_id') if hasattr(session, 'get') else None)
        teams = Team.query.filter_by(is_active=True)
        if account_id:
            teams = teams.filter_by(account_id=account_id)
        teams = teams.all()
        team_id = request.args.get('team_id')
        if not team_id:
            selected_team_id = None
        else:
            selected_team_id = team_id
    elif current_user.role == 'account_admin':
        account_id = current_user.account_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
        team_id = request.args.get('team_id') or (session.get('selected_team_id') if hasattr(session, 'get') else None)
        selected_team_id = team_id
    else:
        account_id = current_user.account_id
        team_id = current_user.team_id
        accounts = [Account.query.get(account_id)] if account_id else []
        teams = [Team.query.get(team_id)] if team_id else []
        selected_team_id = team_id
    # Always show Application dropdown if app_names is available
    return render_template('escalation_matrix.html', app_names=app_names, matrix_data=matrix_data, selected_app=selected_app, accounts=accounts, teams=teams, selected_account_id=account_id, selected_team_id=selected_team_id)

