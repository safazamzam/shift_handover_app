
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models.models import User, Account, Team
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)

# Add route to set account/team selection in session
@auth_bp.route('/set_selection', methods=['POST'])
@login_required
def set_selection():
    account_id = request.form.get('account_id', type=int)
    team_id = request.form.get('team_id', type=int)
    if current_user.role == 'super_admin':
        session['selected_account_id'] = account_id
        session['selected_team_id'] = team_id
    elif current_user.role == 'account_admin':
        session['selected_account_id'] = current_user.account_id
        session['selected_team_id'] = team_id
    # Team admin/user: do not allow changing
    return redirect(request.referrer or url_for('dashboard.dashboard'))

# Make accounts/teams available in all templates
@auth_bp.app_context_processor
def inject_accounts_teams():
    accounts = Account.query.filter_by(is_active=True).all() if current_user.is_authenticated and current_user.role in ['super_admin', 'account_admin'] else []
    selected_account_id = session.get('selected_account_id')
    teams = Team.query.filter_by(account_id=selected_account_id, is_active=True).all() if selected_account_id else []
    return dict(accounts=accounts, teams=teams)

from flask import jsonify

# AJAX endpoint to get teams for a selected account
@auth_bp.route('/get_teams')
def get_teams():
    account_id = request.args.get('account_id')
    teams = []
    if account_id:
        teams = Team.query.filter_by(account_id=account_id, is_active=True).all()
    return jsonify({
        'teams': [{'id': t.id, 'name': t.name} for t in teams]
    })


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    accounts = Account.query.filter_by(is_active=True).all()
    selected_account_id = request.form.get('account_id')
    selected_team_id = request.form.get('team_id')
    # Convert to int if present, else None
    selected_account_id_int = int(selected_account_id) if selected_account_id and selected_account_id.isdigit() else None
    selected_team_id_int = int(selected_team_id) if selected_team_id and selected_team_id.isdigit() else None
    teams = []
    if selected_account_id_int:
        teams = Team.query.filter_by(account_id=selected_account_id_int, is_active=True).all()

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.role == 'super_admin':
            # Super Admin: no account/team required
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Invalid credentials')
        elif user and user.role == 'account_admin':
            # Account Admin: must match username/account, team optional
            if selected_account_id_int == user.account_id and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Invalid credentials or account mismatch')
        elif user and user.role == 'team_admin':
            # Team Admin: must match username/account/team
            if selected_account_id_int == user.account_id and selected_team_id_int == user.team_id and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Invalid credentials or team/account mismatch')
        elif user and user.role == 'user':
            # Regular User: must match username/account/team
            if selected_account_id_int == user.account_id and selected_team_id_int == user.team_id and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Invalid credentials or team/account mismatch')
        else:
            flash('Invalid credentials or role')
    return render_template('login.html', accounts=accounts, teams=teams, selected_account_id=selected_account_id_int, selected_team_id=selected_team_id_int)

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models.models import User, Account, Team
from werkzeug.security import check_password_hash

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

