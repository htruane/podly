"""add segment review functionality

Revision ID: segment_review_001
Revises: fa3a95ecd67d
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'segment_review_001'
down_revision = 'fa3a95ecd67d'
branch_labels = None
depends_on = None


def upgrade():
    # Add segments_approved column to processing_job table
    op.add_column('processing_job', sa.Column('segments_approved', sa.Boolean(), nullable=False, server_default='0'))

    # Update total_steps default to 5 (was 4)
    with op.batch_alter_table('processing_job', schema=None) as batch_op:
        batch_op.alter_column('total_steps', existing_type=sa.INTEGER(), server_default='5')

    # Create segment_override table
    op.create_table(
        'segment_override',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('user_approved', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop segment_override table
    op.drop_table('segment_override')

    # Remove segments_approved column
    op.drop_column('processing_job', 'segments_approved')

    # Revert total_steps default to 4
    with op.batch_alter_table('processing_job', schema=None) as batch_op:
        batch_op.alter_column('total_steps', existing_type=sa.INTEGER(), server_default='4')
