"""
Revision ID: add_user_role_column
Revises: 
Create Date: 2025-08-12

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('user', sa.Column('role', sa.String(length=16), nullable=False, server_default='viewer'))

def downgrade():
    op.drop_column('user', 'role')
