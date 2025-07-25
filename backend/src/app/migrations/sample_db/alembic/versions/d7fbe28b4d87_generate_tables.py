"""generate tables

Revision ID: d7fbe28b4d87
Revises: 
Create Date: 2025-07-16 10:31:02.100506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import ForeignKey, Boolean, JSON, ARRAY, Integer, String, Text, Date, DECIMAL
from sqlalchemy_utils import EmailType, PasswordType, PhoneNumberType, ChoiceType
from src.app.model.enums import AcctType, CurType, EntryType, ItemType, UnitType, EntityType, PropertyType, PropertyTransactionType

# revision identifiers, used by Alembic.
revision: str = 'd7fbe28b4d87'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('chart_of_account',
    sa.Column('chart_id', sa.String(length=13), nullable=False),
    sa.Column('node_name', sa.String(length=50), nullable=False),
    sa.Column('acct_type', ChoiceType(AcctType, impl = Integer()), nullable=False),
    sa.Column('parent_chart_id', sa.String(length=13), nullable=True),
    sa.ForeignKeyConstraint(['parent_chart_id'], ['chart_of_account.chart_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('chart_id'),
    sa.UniqueConstraint('node_name')
    )
    op.create_table('contact',
    sa.Column('contact_id', sa.String(length=13), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('email', EmailType(length=255), nullable=False),
    sa.Column('phone', PhoneNumberType(length=20), nullable=True),
    sa.Column('address', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('contact_id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('file',
    sa.Column('file_id', sa.String(length=18), nullable=False),
    sa.Column('filename', sa.String(length=200), nullable=False),
    sa.Column('filehash', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('file_id'),
    sa.UniqueConstraint('filehash'),
    sa.UniqueConstraint('filename')
    )
    op.create_table('journals',
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('jrn_date', sa.Date(), nullable=False),
    sa.Column('jrn_src', ChoiceType(CurType, impl = Integer()), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('journal_id')
    )
    op.create_table('accounts',
    sa.Column('acct_id', sa.String(length=15), nullable=False),
    sa.Column('acct_name', sa.String(length=50), nullable=False),
    sa.Column('acct_type', ChoiceType(AcctType, impl = Integer()), nullable=False),
    sa.Column('currency', ChoiceType(CurType, impl = Integer()), nullable=True),
    sa.Column('chart_id', sa.String(length=13), nullable=False),
    sa.ForeignKeyConstraint(['chart_id'], ['chart_of_account.chart_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('acct_id'),
    sa.UniqueConstraint('acct_name')
    )
    op.create_table('entity',
    sa.Column('entity_id', sa.String(length=13), nullable=False),
    sa.Column('entity_type', ChoiceType(EntityType, impl = Integer()), nullable=False),
    sa.Column('entity_name', sa.String(length=50), nullable=False),
    sa.Column('is_business', sa.Boolean(create_constraint=True), nullable=False),
    sa.Column('bill_contact_id', sa.String(length=13), nullable=False),
    sa.Column('ship_same_as_bill', sa.Boolean(create_constraint=True), nullable=False),
    sa.Column('ship_contact_id', sa.String(length=13), nullable=False),
    sa.ForeignKeyConstraint(['bill_contact_id'], ['contact.contact_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['ship_contact_id'], ['contact.contact_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('entity_type', 'entity_name'),
    sa.UniqueConstraint('entity_id')
    )
    op.create_table('dividend',
    sa.Column('div_id', sa.String(length=15), nullable=False),
    sa.Column('div_dt', sa.Date(), nullable=False),
    sa.Column('div_amt', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('credit_acct_id', sa.String(length=15), nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['credit_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('div_id')
    )
    op.create_table('entries',
    sa.Column('entry_id', sa.String(length=20), nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('entry_type', ChoiceType(EntryType, impl = Integer()), nullable=False),
    sa.Column('acct_id', sa.String(length=15), nullable=False),
    sa.Column('cur_incexp', ChoiceType(CurType, impl = Integer()), nullable=True),
    sa.Column('amount', sa.DECIMAL(precision=18, scale=6, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('amount_base', sa.DECIMAL(precision=18, scale=6, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('entry_id')
    )
    op.create_table('expense',
    sa.Column('expense_id', sa.String(length=15), nullable=False),
    sa.Column('expense_dt', sa.Date(), nullable=False),
    sa.Column('currency', ChoiceType(CurType, impl = Integer()), nullable=False),
    sa.Column('payment_acct_id', sa.String(length=15), nullable=False),
    sa.Column('payment_amount', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('exp_info', sa.JSON(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('receipts', sa.JSON(), nullable=True),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['payment_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('expense_id')
    )
    op.create_table('invoice',
    sa.Column('invoice_id', sa.String(length=13), nullable=False),
    sa.Column('invoice_num', sa.String(length=25), nullable=False),
    sa.Column('invoice_dt', sa.Date(), nullable=False),
    sa.Column('due_dt', sa.Date(), nullable=True),
    sa.Column('entity_id', sa.String(length=13), nullable=False),
    sa.Column('entity_type', ChoiceType(EntityType, impl = Integer()), nullable=False),
    sa.Column('subject', sa.String(length=50), nullable=False),
    sa.Column('currency', ChoiceType(CurType, impl = Integer()), nullable=False),
    sa.Column('shipping', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['entity_id'], ['entity.entity_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('invoice_id'),
    sa.UniqueConstraint('invoice_num')
    )
    op.create_table('item',
    sa.Column('item_id', sa.String(length=13), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('item_type', ChoiceType(ItemType, impl = Integer()), nullable=False),
    sa.Column('entity_type', ChoiceType(EntityType, impl = Integer()), nullable=False),
    sa.Column('unit', ChoiceType(UnitType, impl = Integer()), nullable=False),
    sa.Column('unit_price', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('currency', ChoiceType(CurType, impl = Integer()), nullable=True),
    sa.Column('default_acct_id', sa.String(length=15), nullable=False),
    sa.ForeignKeyConstraint(['default_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('item_id')
    )
    op.create_table('payment',
    sa.Column('payment_id', sa.String(length=15), nullable=False),
    sa.Column('payment_num', sa.String(length=25), nullable=False),
    sa.Column('payment_dt', sa.Date(), nullable=False),
    sa.Column('entity_type', ChoiceType(EntityType, impl = Integer()), nullable=False),
    sa.Column('payment_acct_id', sa.String(length=15), nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('payment_fee', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('ref_num', sa.Text(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['payment_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('payment_id'),
    sa.UniqueConstraint('payment_num')
    )
    op.create_table('property',
    sa.Column('property_id', sa.String(length=14), nullable=False),
    sa.Column('property_name', sa.String(length=50), nullable=False),
    sa.Column('property_type', ChoiceType(PropertyType, impl = Integer()), nullable=False),
    sa.Column('pur_dt', sa.Date(), nullable=False),
    sa.Column('pur_price', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('tax', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('pur_acct_id', sa.String(length=15), nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('receipts', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['pur_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('property_id')
    )
    op.create_table('stock_repurchase',
    sa.Column('repur_id', sa.String(length=15), nullable=False),
    sa.Column('repur_dt', sa.Date(), nullable=False),
    sa.Column('num_shares', sa.DECIMAL(precision=17, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('repur_price', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('credit_acct_id', sa.String(length=15), nullable=False),
    sa.Column('repur_amt', sa.DECIMAL(precision=17, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['credit_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('repur_id')
    )
    op.create_table('expense_item',
    sa.Column('expense_item_id', sa.String(length=20), nullable=False),
    sa.Column('expense_id', sa.String(length=15), nullable=False),
    sa.Column('expense_acct_id', sa.String(length=15), nullable=False),
    sa.Column('amount_pre_tax', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('tax_rate', sa.DECIMAL(precision=15, scale=4, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['expense_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['expense_id'], ['expense.expense_id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('expense_item_id')
    )
    op.create_table('general_invoice_item',
    sa.Column('ginv_item_id', sa.String(length=17), nullable=False),
    sa.Column('invoice_id', sa.String(length=13), nullable=False),
    sa.Column('incur_dt', sa.Date(), nullable=False),
    sa.Column('acct_id', sa.String(length=15), nullable=False),
    sa.Column('currency', ChoiceType(CurType, impl = Integer()), nullable=False),
    sa.Column('amount_pre_tax_raw', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('amount_pre_tax', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('tax_rate', sa.DECIMAL(precision=15, scale=4, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoice.invoice_id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('ginv_item_id')
    )
    op.create_table('invoice_item',
    sa.Column('invoice_item_id', sa.String(length=17), nullable=False),
    sa.Column('invoice_id', sa.String(length=13), nullable=False),
    sa.Column('item_id', sa.String(length=13), nullable=False),
    sa.Column('quantity', sa.DECIMAL(precision=18, scale=8, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('acct_id', sa.String(length=15), nullable=False),
    sa.Column('tax_rate', sa.DECIMAL(precision=15, scale=4, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('discount_rate', sa.DECIMAL(precision=15, scale=4, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoice.invoice_id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['item.item_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('invoice_item_id')
    )
    op.create_table('payment_item',
    sa.Column('payment_item_id', sa.String(length=18), nullable=False),
    sa.Column('payment_id', sa.String(length=15), nullable=False),
    sa.Column('invoice_id', sa.String(length=13), nullable=False),
    sa.Column('payment_amount', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('payment_amount_raw', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoice.invoice_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['payment_id'], ['payment.payment_id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('payment_item_id')
    )
    op.create_table('property_trans',
    sa.Column('trans_id', sa.String(length=18), nullable=False),
    sa.Column('property_id', sa.String(length=14), nullable=False),
    sa.Column('trans_dt', sa.Date(), nullable=False),
    sa.Column('trans_type', ChoiceType(PropertyTransactionType, impl = Integer()), nullable=False),
    sa.Column('trans_amount', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['property_id'], ['property.property_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('trans_id')
    )
    op.create_table('stock_issue',
    sa.Column('issue_id', sa.String(length=15), nullable=False),
    sa.Column('issue_dt', sa.Date(), nullable=False),
    sa.Column('is_reissue', sa.Boolean(create_constraint=True), nullable=False),
    sa.Column('num_shares', sa.DECIMAL(precision=17, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('issue_price', sa.DECIMAL(precision=15, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('reissue_repur_id', sa.String(length=15), nullable=True),
    sa.Column('debit_acct_id', sa.String(length=15), nullable=False),
    sa.Column('issue_amt', sa.DECIMAL(precision=17, scale=3, asdecimal=False), server_default='0.0', nullable=False),
    sa.Column('journal_id', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['debit_acct_id'], ['accounts.acct_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['journal_id'], ['journals.journal_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reissue_repur_id'], ['stock_repurchase.repur_id'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('issue_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('stock_issue')
    op.drop_table('property_trans')
    op.drop_table('payment_item')
    op.drop_table('invoice_item')
    op.drop_table('general_invoice_item')
    op.drop_table('expense_item')
    op.drop_table('stock_repurchase')
    op.drop_table('property')
    op.drop_table('payment')
    op.drop_table('item')
    op.drop_table('invoice')
    op.drop_table('expense')
    op.drop_table('entries')
    op.drop_table('dividend')
    op.drop_table('entity')
    op.drop_table('accounts')
    op.drop_table('journals')
    op.drop_table('file')
    op.drop_table('contact')
    op.drop_table('chart_of_account')
    # ### end Alembic commands ###
