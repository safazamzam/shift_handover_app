from app import app, db
from models.models import Account, Team, User, TeamMember
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create Accounts
    accounts = []
    for acc_name in ['Acme Corp', 'Beta Inc']:
        acc = Account.query.filter_by(name=acc_name).first()
        if not acc:
            acc = Account(name=acc_name)
            db.session.add(acc)
            db.session.commit()
        accounts.append(acc)

    # Create Teams
    teams = []
    for i, acc in enumerate(accounts):
        for tname in [f"{acc.name} Team A", f"{acc.name} Team B"]:
            t = Team.query.filter_by(name=tname, account_id=acc.id).first()
            if not t:
                t = Team(name=tname, account_id=acc.id)
                db.session.add(t)
                db.session.commit()
            teams.append(t)

    # Create Super Admin
    super_admin = User.query.filter_by(username='superadmin').first()
    if not super_admin:
        super_admin = User(username='superadmin', email='superadmin@example.com', password=generate_password_hash('superadmin123'), role='super_admin', account_id=None, team_id=None)
        db.session.add(super_admin)
        db.session.commit()

    # Create Account Admins
    for i, acc in enumerate(accounts):
        acc_admin = User.query.filter_by(username=f"accadmin{i+1}").first()
        if not acc_admin:
            acc_admin = User(username=f"accadmin{i+1}", email=f"accadmin{i+1}@example.com", password=generate_password_hash(f"accadmin{i+1}123"), role='account_admin', account_id=acc.id, team_id=None)
            db.session.add(acc_admin)
    db.session.commit()

    # Create Team Admins and Users
    for i, team in enumerate(teams):
        acc = next(a for a in accounts if a.id == team.account_id)
        # Team Admin
        tadmin = User.query.filter_by(username=f"{team.name.lower().replace(' ', '_')}_admin").first()
        if not tadmin:
            tadmin = User(username=f"{team.name.lower().replace(' ', '_')}_admin", email=f"{team.name.lower().replace(' ', '_')}_admin@example.com", password=generate_password_hash('admin123'), role='team_admin', account_id=acc.id, team_id=team.id)
            db.session.add(tadmin)
            db.session.commit()
        # Team Users
        for uidx in range(1, 3):
            uname = f"{team.name.lower().replace(' ', '_')}_user{uidx}"
            u = User.query.filter_by(username=uname).first()
            if not u:
                u = User(username=uname, email=f"{uname}@example.com", password=generate_password_hash(f"user{uidx}123"), role='user', account_id=acc.id, team_id=team.id)
                db.session.add(u)
        db.session.commit()

    # Add Team Members for all users in each team
    for team in teams:
        users = User.query.filter_by(team_id=team.id).all()
        for user in users:
            if not TeamMember.query.filter_by(user_id=user.id, team_id=team.id).first():
                db.session.add(TeamMember(user_id=user.id, team_id=team.id, name=user.username, email=user.email, contact_number='1234567890', role=user.role, account_id=user.account_id))
        db.session.commit()

    print('Seed data inserted successfully!')
