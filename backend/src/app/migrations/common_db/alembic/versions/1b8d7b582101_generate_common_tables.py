"""generate_common_tables

Revision ID: 1b8d7b582101
Revises: 
Create Date: 2025-07-17 12:30:03.130463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import ForeignKey, Boolean, JSON, ARRAY, Integer, String, Text, Date, DECIMAL
from sqlalchemy_utils import EmailType, PasswordType, PhoneNumberType, ChoiceType
from src.app.model.enums import AcctType, CurType, EntryType, ItemType, UnitType, EntityType, PropertyType, PropertyTransactionType


# revision identifiers, used by Alembic.
revision: str = '1b8d7b582101'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('currency',
    sa.Column('currency', ChoiceType(CurType, impl = Integer()), nullable=False),
    sa.Column('cur_dt', sa.Date(), nullable=False),
    sa.Column('rate', sa.DECIMAL(precision=15, scale=5, asdecimal=False), nullable=False),
    sa.PrimaryKeyConstraint('currency', 'cur_dt')
    )
    
    op.create_table('users',
    sa.Column('user_id', sa.String(length=15), nullable=False),
    sa.Column('username', sa.String(length=20), nullable=False),
    sa.Column('hashed_password', sa.String(length=72), nullable=False),
    sa.Column('is_admin', sa.Boolean(create_constraint=True), nullable=False),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('username')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('currency')
    op.drop_table('users')
    # ### end Alembic commands ###
