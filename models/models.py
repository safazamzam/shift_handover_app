
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
from flask_login import UserMixin

# Multi-account and multi-team support
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')  # 'active', 'disabled'
    teams = db.relationship('Team', backref='account', lazy=True)
    users = db.relationship('User', backref='account', lazy=True)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')  # 'active', 'disabled'
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    members = db.relationship('TeamMember', backref='team', lazy=True)
    users = db.relationship('User', backref='team', lazy=True)

# Escalation Matrix File model for persistent uploads
class EscalationMatrixFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    upload_time = db.Column(db.DateTime, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

class ShiftRoster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=False)
    shift_code = db.Column(db.String(8), nullable=True)  # E, D, N, G, LE, VL, HL, CO, or blank
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='user')  # 'super_admin', 'account_admin', 'team_admin', 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')  # 'active', 'disabled'
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(32), nullable=False)
    role = db.Column(db.String(64))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    current_shift_type = db.Column(db.String(16), nullable=False) # Morning/Evening/Night
    next_shift_type = db.Column(db.String(16), nullable=False)
    current_engineers = db.relationship('TeamMember', secondary='current_shift_engineers')
    next_engineers = db.relationship('TeamMember', secondary='next_shift_engineers')
    status = db.Column(db.String(16), nullable=False, default='draft')  # draft or sent
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(16), nullable=False) # Active/Closed
    priority = db.Column(db.String(16), nullable=False)
    handover = db.Column(db.Text)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    type = db.Column(db.String(32), nullable=False) # Active, Closed, Priority, Handover
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)


class ShiftKeyPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False) # Open/Closed/In Progress
    responsible_engineer_id = db.Column(db.Integer, db.ForeignKey('team_member.id'))
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    jira_id = db.Column(db.String(64), nullable=True)  # New field for JIRA ID
    updates = db.relationship('ShiftKeyPointUpdate', backref='key_point', lazy=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

# Daily updates for key points
class ShiftKeyPointUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_point_id = db.Column(db.Integer, db.ForeignKey('shift_key_point.id'), nullable=False)
    update_text = db.Column(db.Text, nullable=False)
    update_date = db.Column(db.Date, nullable=False)
    updated_by = db.Column(db.String(64), nullable=False)

# Association tables
current_shift_engineers = db.Table('current_shift_engineers',
    db.Column('shift_id', db.Integer, db.ForeignKey('shift.id')),
    db.Column('team_member_id', db.Integer, db.ForeignKey('team_member.id'))
)

next_shift_engineers = db.Table('next_shift_engineers',
    db.Column('shift_id', db.Integer, db.ForeignKey('shift.id')),
    db.Column('team_member_id', db.Integer, db.ForeignKey('team_member.id'))
)

