from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.models import db, Account, Team, User
from werkzeug.security import generate_password_hash

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['super_admin', 'account_admin']:
            flash('Access denied.')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated

admin_bp = Blueprint('admin', __name__)

# --- Account Management ---
@admin_bp.route('/accounts')
@login_required
@admin_required
def accounts():
    accounts = Account.query.all()
    return render_template('admin/accounts.html', accounts=accounts)

@admin_bp.route('/accounts/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_account():
    if request.method == 'POST':
        name = request.form['name']
        if Account.query.filter_by(name=name).first():
            flash('Account already exists.')
        else:
            db.session.add(Account(name=name))
            db.session.commit()
            flash('Account added.')
            return redirect(url_for('admin.accounts'))
    return render_template('admin/account_form.html', action='Add')

@admin_bp.route('/accounts/edit/<int:account_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    if request.method == 'POST':
        account.name = request.form['name']
        db.session.commit()
        flash('Account updated.')
        return redirect(url_for('admin.accounts'))
    return render_template('admin/account_form.html', action='Edit', account=account)

@admin_bp.route('/accounts/delete/<int:account_id>', methods=['POST'])
@login_required
@admin_required
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    flash('Account deleted.')
    return redirect(url_for('admin.accounts'))

# --- Team Management ---
@admin_bp.route('/teams')
@login_required
@admin_required
def teams():
    teams = Team.query.all()
    return render_template('admin/teams.html', teams=teams)

@admin_bp.route('/teams/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_team():
    accounts = Account.query.all()
    if request.method == 'POST':
        name = request.form['name']
        account_id = request.form['account_id']
        if Team.query.filter_by(name=name, account_id=account_id).first():
            flash('Team already exists.')
        else:
            db.session.add(Team(name=name, account_id=account_id))
            db.session.commit()
            flash('Team added.')
            return redirect(url_for('admin.teams'))
    return render_template('admin/team_form.html', action='Add', accounts=accounts)

@admin_bp.route('/teams/edit/<int:team_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    accounts = Account.query.all()
    if request.method == 'POST':
        team.name = request.form['name']
        team.account_id = request.form['account_id']
        db.session.commit()
        flash('Team updated.')
        return redirect(url_for('admin.teams'))
    return render_template('admin/team_form.html', action='Edit', team=team, accounts=accounts)

@admin_bp.route('/teams/delete/<int:team_id>', methods=['POST'])
@login_required
@admin_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted.')
    return redirect(url_for('admin.teams'))

# --- User Management ---
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    accounts = Account.query.all()
    teams = Team.query.all()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        account_id = request.form['account_id']
        team_id = request.form['team_id'] or None
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
        else:
            db.session.add(User(username=username, email=email, password=password, role=role, account_id=account_id, team_id=team_id))
            db.session.commit()
            flash('User added.')
            return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', action='Add', accounts=accounts, teams=teams)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    accounts = Account.query.all()
    teams = Team.query.all()
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])
        user.role = request.form['role']
        user.account_id = request.form['account_id']
        user.team_id = request.form['team_id'] or None
        db.session.commit()
        flash('User updated.')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', action='Edit', user=user, accounts=accounts, teams=teams)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.')
    return redirect(url_for('admin.users'))
