"""Add browsing history model

Revision ID: b290d2a248eb
Revises: 2fb62f695ba2
Create Date: 2025-06-22 04:26:28.898397

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b290d2a248eb'
down_revision = '2fb62f695ba2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('browsing_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timestamp', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('view_count', sa.Integer(), nullable=True))
        batch_op.drop_column('viewed_at')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('browsing_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('viewed_at', mysql.DATETIME(), nullable=True))
        batch_op.drop_column('view_count')
        batch_op.drop_column('timestamp')

    # ### end Alembic commands ###
