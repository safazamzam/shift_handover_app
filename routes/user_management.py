
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.models import db, User, Account, Team
from werkzeug.security import generate_password_hash

user_mgmt_bp = Blueprint('user_mgmt', __name__)

@user_mgmt_bp.route('/user-management', methods=['GET', 'POST'])
@login_required
def user_management():
    # Role-based filtering
    # Only show active users, teams, and accounts by default
    if current_user.role == 'super_admin':
        users = User.query.filter(User.status.in_(['active', 'disabled'])).all()
        accounts = Account.query.filter(Account.status.in_(['active', 'disabled'])).all()
        teams = Team.query.filter(Team.status.in_(['active', 'disabled'])).all()
    elif current_user.role == 'account_admin':
        users = User.query.filter(User.account_id==current_user.account_id, User.status.in_(['active', 'disabled'])).all()
        acc = Account.query.get(current_user.account_id)
        accounts = [acc] if acc and acc.status in ['active', 'disabled'] else []
        teams = Team.query.filter(Team.account_id==current_user.account_id, Team.status.in_(['active', 'disabled'])).all()
    elif current_user.role == 'team_admin':
        users = User.query.filter(User.account_id==current_user.account_id, User.team_id==current_user.team_id, User.status.in_(['active', 'disabled'])).all()
        acc = Account.query.get(current_user.account_id)
        accounts = [acc] if acc and acc.status in ['active', 'disabled'] else []
        t = Team.query.get(current_user.team_id)
        teams = [t] if t and t.status in ['active', 'disabled'] else []
    else:
        flash('You do not have permission to access user management.')
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        print(f"[POST RECEIVED] user_management: user={getattr(current_user, 'username', None)}, action={request.form.get('action')}, form={dict(request.form)}")
        action = request.form.get('action')
        # Enable/disable user
        if action in ['enable_user', 'disable_user']:
            user_id = request.form.get('user_id', type=int)
            user = User.query.get(user_id)
            if user:
                # Only allow within scope
                if current_user.role == 'super_admin' or \
                   (current_user.role == 'account_admin' and user.account_id == current_user.account_id and user.role != 'super_admin') or \
                   (current_user.role == 'team_admin' and user.account_id == current_user.account_id and user.team_id == current_user.team_id and user.role == 'user'):
                    user.is_active = (action == 'enable_user')
                    user.status = 'active' if action == 'enable_user' else 'disabled'
                    db.session.commit()
                    flash(f"User {'enabled' if action == 'enable_user' else 'disabled'} successfully.")
                else:
                    flash('You do not have permission to enable/disable this user.')
            else:
                flash('User not found.')
            return redirect(url_for('user_mgmt.user_management'))
        # Enable/disable team
        elif action in ['enable_team', 'disable_team']:
            team_id = request.form.get('team_id', type=int)
            team = Team.query.get(team_id)
            if team:
                if current_user.role == 'super_admin' or \
                   (current_user.role == 'account_admin' and team.account_id == current_user.account_id):
                    team.is_active = (action == 'enable_team')
                    team.status = 'active' if action == 'enable_team' else 'disabled'
                    db.session.commit()
                    flash(f"Team {'enabled' if action == 'enable_team' else 'disabled'} successfully.")
                else:
                    flash('You do not have permission to enable/disable this team.')
            else:
                flash('Team not found.')
            return redirect(url_for('user_mgmt.user_management'))
        # Enable/disable account
        elif action in ['enable_account', 'disable_account']:
            account_id = request.form.get('account_id', type=int)
            account = Account.query.get(account_id)
            if account:
                if current_user.role == 'super_admin':
                    account.is_active = (action == 'enable_account')
                    account.status = 'active' if action == 'enable_account' else 'disabled'
                    db.session.commit()
                    flash(f"Account {'enabled' if action == 'enable_account' else 'disabled'} successfully.")
                else:
                    flash('You do not have permission to enable/disable this account.')
            else:
                flash('Account not found.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'add_account' and current_user.role == 'super_admin':
            # ...existing code...
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'add_team' and (current_user.role == 'super_admin' or current_user.role == 'account_admin'):
            # ...existing code...
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')
            account_id = request.form.get('account_id', type=int)
            team_id = request.form.get('team_id', type=int)
            debug_msgs = []
            debug_msgs.append(f"[DEBUG] Add User: username={username}, role={role}, account_id={account_id}, team_id={team_id}")
            try:
                if username and password and role and account_id:
                    existing_user = User.query.filter_by(username=username).first()
                    debug_msgs.append(f"[DEBUG] Existing user: {existing_user}")
                    if existing_user:
                        flash('Username already exists.')
                        debug_msgs.append("[ERROR] Username already exists.")
                    else:
                        # Only allow adding within scope
                        if current_user.role == 'super_admin' or \
                           (current_user.role == 'account_admin' and account_id == current_user.account_id) or \
                           (current_user.role == 'team_admin' and account_id == current_user.account_id and team_id == current_user.team_id):
                            user = User(username=username, password=generate_password_hash(password), role=role, account_id=account_id, team_id=team_id if team_id else None, status='active', is_active=True)
                            db.session.add(user)
                            db.session.flush()
                            debug_msgs.append(f"[DEBUG] User (before commit): id={user.id}, username={user.username}")
                            db.session.commit()
                            debug_msgs.append(f"[DEBUG] User created: {user}")
                            flash('User added successfully.')
                        else:
                            flash('You do not have permission to add user to this account/team.')
                            debug_msgs.append("[ERROR] Permission denied for user add.")
                else:
                    flash('All fields except team are required.')
                    debug_msgs.append("[ERROR] Missing required fields for user add.")
            except Exception as e:
                db.session.rollback()
                debug_msgs.append(f"[ERROR] Exception: {e}")
                flash('Failed to add user.')
            finally:
                flash(' | '.join(debug_msgs))
        elif action == 'delete':
            user_id = request.form.get('user_id', type=int)
            user = User.query.get(user_id)
            print(f"[DELETE] Attempting to soft delete user_id={user_id}, found={user}")
            if user and user.username != 'admin':
                # Only allow deleting within scope
                if current_user.role == 'super_admin' or \
                   (current_user.role == 'account_admin' and user.account_id == current_user.account_id) or \
                   (current_user.role == 'team_admin' and user.account_id == current_user.account_id and user.team_id == current_user.team_id):
                    user.status = 'deleted'
                    user.is_active = False
                    db.session.commit()
                    print(f"[DELETE] User soft deleted: {user}")
                    flash('User deleted successfully.')
                else:
                    print(f"[DELETE] Permission denied for user_id={user_id}")
                    flash('You do not have permission to delete this user.')
            else:
                print(f"[DELETE] Cannot delete user_id={user_id}, user={user}")
                flash('Cannot delete this user.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'delete_team':
            team_id = request.form.get('team_id', type=int)
            team = Team.query.get(team_id)
            if team:
                if current_user.role == 'super_admin' or (current_user.role == 'account_admin' and team.account_id == current_user.account_id):
                    team.status = 'deleted'
                    team.is_active = False
                    db.session.commit()
                    flash('Team deleted successfully.')
                else:
                    flash('You do not have permission to delete this team.')
            else:
                flash('Team not found.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'delete_account':
            account_id = request.form.get('account_id', type=int)
            account = Account.query.get(account_id)
            if account:
                if current_user.role == 'super_admin':
                    account.status = 'deleted'
                    account.is_active = False
                    db.session.commit()
                    flash('Account deleted successfully.')
                else:
                    flash('You do not have permission to delete this account.')
            else:
                flash('Account not found.')
            return redirect(url_for('user_mgmt.user_management'))
        elif action == 'update':
            user_id = request.form.get('user_id', type=int)
            role = request.form.get('role')
            user = User.query.get(user_id)
            if user:
                # Only allow updating within scope
                if current_user.role == 'super_admin':
                    users = User.query.filter(User.status.in_(['active', 'disabled'])).all()
                    accounts = Account.query.all()
                    teams = Team.query.all()
                elif current_user.role == 'account_admin':
                    users = User.query.filter(User.account_id==current_user.account_id, User.status.in_(['active', 'disabled'])).all()
                    acc = Account.query.get(current_user.account_id)
                    accounts = [acc] if acc else []
                    teams = Team.query.filter_by(account_id=current_user.account_id).all()
                elif current_user.role == 'team_admin':
                    users = User.query.filter(User.account_id==current_user.account_id, User.team_id==current_user.team_id, User.status.in_(['active', 'disabled'])).all()
                    acc = Account.query.get(current_user.account_id)
                    accounts = [acc] if acc else []
                    t = Team.query.get(current_user.team_id)
                    teams = [t] if t else []
    return render_template('user_management.html', users=users, accounts=accounts, teams=teams)
