from app import db

class KBDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_name = db.Column(db.String(128), nullable=False)
    issue = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False)
    kb_number = db.Column(db.String(64), unique=True, nullable=False)
