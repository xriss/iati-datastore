"""Add crawler tables

Revision ID: 1c0c431c5703
Revises: None
Create Date: 2013-03-13 18:15:00.855207

"""

# revision identifiers, used by Alembic.
revision = '1c0c431c5703'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('dataset',
    sa.Column('name', sa.Unicode(), nullable=False),
    sa.Column('first_seen', sa.DateTime(), nullable=False),
    sa.Column('last_seen', sa.DateTime(), nullable=False),
    sa.Column('last_modified', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('name')
    )
    op.create_table('resource',
    sa.Column('url', sa.Unicode(), nullable=False),
    sa.Column('dataset_id', sa.Unicode(), nullable=True),
    sa.Column('last_fetch', sa.DateTime(), nullable=True),
    sa.Column('last_status_code', sa.Integer(), nullable=True),
    sa.Column('last_succ', sa.DateTime(), nullable=True),
    sa.Column('document', sa.UnicodeText(), nullable=True),
    sa.Column('etag', sa.Unicode(), nullable=True),
    sa.ForeignKeyConstraint(['dataset_id'], ['dataset.name'], ),
    sa.PrimaryKeyConstraint('url')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('resource')
    op.drop_table('dataset')
    ### end Alembic commands ###
