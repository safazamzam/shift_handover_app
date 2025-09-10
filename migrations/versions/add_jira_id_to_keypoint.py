"""
Revision ID: add_jira_id_to_keypoint
Revises: 
Create Date: 2025-08-10
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('shift_key_point', sa.Column('jira_id', sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column('shift_key_point', 'jira_id')
