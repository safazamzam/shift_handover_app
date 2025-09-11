from app import db

class VendorDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_name = db.Column(db.String(128), nullable=False)
    vendor_name = db.Column(db.String(128), nullable=False)
    contact_name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(128), nullable=False)
