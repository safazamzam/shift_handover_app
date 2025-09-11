"""
Add ApplicationDetail table
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'application_detail',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('purpose', sa.String(length=256), nullable=False),
        sa.Column('recording_link', sa.String(length=256), nullable=False),
        sa.Column('documents_link', sa.String(length=256), nullable=False)
    )

def downgrade():
    op.drop_table('application_detail')
