# This service can be used for additional DB operations if needed
from app import db

def commit_changes():
    db.session.commit()
