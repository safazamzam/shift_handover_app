"""
Migration script to add 'status' column to Shift table.
Run this script once with your Flask app context.
"""
from app import db
from models.models import Shift
from sqlalchemy import Column, String, text

def upgrade():
    # Add 'status' column to Shift table if not exists
    with db.engine.connect() as conn:
        conn.execute(text('ALTER TABLE shift ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT "draft";'))

from app import app
if __name__ == "__main__":
    with app.app_context():
        upgrade()
        print("Migration complete: 'status' column added to Shift table.")
