"""Add Google authentication fields to User model

Revision ID: google_auth_fields
Revises: 
Create Date: 2025-05-03 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'google_auth_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add Google authentication fields to users table
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True, unique=True))
    op.add_column('users', sa.Column('profile_picture', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(50), nullable=True, server_default='local'))
    
    # Create index for google_id
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)


def downgrade():
    # Drop Google authentication fields from users table
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'profile_picture')
    op.drop_column('users', 'google_id')
