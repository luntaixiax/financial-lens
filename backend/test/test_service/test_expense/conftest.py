
from datetime import date
import pytest
from src.app.model.enums import CurType
from src.app.model.expense import Expense, ExpenseItem, Merchant
from src.app.utils.tools import get_base_cur


@pytest.fixture
def sample_expense_meal() -> Expense: 
    expense = Expense(
        expense_dt=date(2024, 1, 1),
        currency=get_base_cur(),
        expense_items=[
            ExpenseItem(
                expense_item_id='sample-exp-item1',
                expense_acct_id='acct-meal',
                amount_pre_tax=98,
                tax_rate=0.13,
                description='4 course meals'
            ),
            ExpenseItem(
                expense_item_id='sample-exp-item2',
                expense_acct_id='acct-tip',
                amount_pre_tax=13,
                tax_rate=0,
                description='tip for server'
            )
        ],
        payment_acct_id='acct-credit', # same currency
        payment_amount=123.74,
        merchant=Merchant(
            merchant='Good Taste Sushi',
            platform='Uber Eats',
            ref_no='ub12345'
        ),
        note='Meal for client gathering',
        receipts=[
            'invoice.png',
            'receipt.pdf'
        ]
    )
    return expense

@pytest.fixture
def sample_expense_rent() -> Expense: 
    expense = Expense(
        expense_dt=date(2024, 1, 1),
        currency=CurType.EUR, # different currency
        expense_items=[
            ExpenseItem(
                expense_item_id='sample-exp-item3',
                expense_acct_id='acct-rental',
                amount_pre_tax=980,
                tax_rate=0.13,
                description=None
            )
        ],
        payment_acct_id='acct-credit', # different currency
        payment_amount=1250, # paid EUR1250
        merchant=Merchant(
            merchant='Shareholder',
            platform=None,
            ref_no='RENT-20240101'
        ),
        note='Rent for 2024-01-01',
        receipts=None
    )
    return expense