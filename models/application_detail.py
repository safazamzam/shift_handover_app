from app import db

class ApplicationDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    purpose = db.Column(db.String(256), nullable=False)
    recording_link = db.Column(db.String(256), nullable=False)
    documents_link = db.Column(db.String(256), nullable=False)
