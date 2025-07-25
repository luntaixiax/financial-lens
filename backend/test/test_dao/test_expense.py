from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.enums import CurType
from src.app.model.expense import ExpenseItem, Expense, ExpInfo, Merchant

@pytest.fixture
def sample_expense_meal(test_setting_service) -> Expense: 
    expense = Expense(
        expense_dt=date(2024, 1, 1),
        currency=test_setting_service.get_base_currency(),
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
        payment_acct_id='acct-credit',
        payment_amount=123.74,
        exp_info=ExpInfo(
            merchant=Merchant(
                merchant='Good Taste Sushi',
                platform='Uber Eats',
                ref_no='ub12345'
            ),
            external_pmt_acct='BNS Amex'
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
        currency=CurType.EUR,
        expense_items=[
            ExpenseItem(
                expense_item_id='sample-exp-item3',
                expense_acct_id='acct-rental',
                amount_pre_tax=98,
                tax_rate=0.13,
                description=None
            )
        ],
        payment_acct_id='acct-shareloan',
        payment_amount=110.74,
        exp_info=ExpInfo(
            merchant=Merchant(
                merchant='Shareholder',
                platform=None,
                ref_no='RENT-20240101'
            ),
            external_pmt_acct='Scotia Check'
        ),
        note='Rent for 2024-01-01',
        receipts=None
    )
    return expense

def test_expense(session_with_sample_choa, 
                 sample_expense_meal, sample_expense_rent, sample_journal_meal,
                 test_expense_dao, test_journal_dao):
    
    # add without journal will fail
    with pytest.raises(FKNotExistError):
        test_expense_dao.add(journal_id = 'test-jrn', expense = sample_expense_meal)
    
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # finally you can add invoice
    test_expense_dao.add(
        journal_id = sample_journal_meal.journal_id, 
        expense = sample_expense_meal
    )
    test_expense_dao.add(
        journal_id = sample_journal_meal.journal_id, 
        expense = sample_expense_rent
    )
    
    # test get expense
    _expense, _jrn_id = test_expense_dao.get(sample_expense_meal.expense_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _expense == sample_expense_meal
    _expense, _jrn_id = test_expense_dao.get(sample_expense_rent.expense_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _expense == sample_expense_rent
    
    # test summary expense
    test_expense_dao.summary_expense(date(2000, 1, 1), date(2099, 12, 31))
    
    # test remove invoice
    test_expense_dao.remove(sample_expense_meal.expense_id)
    with pytest.raises(NotExistError):
        test_expense_dao.get(sample_expense_meal.expense_id)
    test_expense_dao.remove(sample_expense_rent.expense_id)
    with pytest.raises(NotExistError):
        test_expense_dao.get(sample_expense_rent.expense_id)
    
    # test add expense with non-exist account id
    sample_expense_meal.payment_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        test_expense_dao.add(journal_id = 'test-jrn', expense = sample_expense_meal)
        
    test_journal_dao.remove(sample_journal_meal.journal_id)