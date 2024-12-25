from datetime import date
import logging
import math
import pytest
from unittest import mock
from src.app.utils.tools import get_base_cur
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import CurType, ItemType, JournalSrc, UnitType
from src.app.model.expense import Expense, ExpenseItem, Merchant
from src.app.model.const import SystemAcctNumber

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_expense(mock_engine, engine_with_sample_choa, sample_expense_meal, sample_expense_rent):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.expense import ExpenseService
    from src.app.service.fx import FxService
    from src.app.service.acct import AcctService
    
    # test same currency expense
    journal = ExpenseService.create_journal_from_expense(sample_expense_meal)
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.EXPENSE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # total amount from expense should be same to total amount from journal (base currency)
    total_expense = FxService.convert(
        amount=sample_expense_meal.total, # total expense
        src_currency=sample_expense_meal.currency, # expense currency
        cur_dt=sample_expense_meal.expense_dt, # convert fx at expense date
    )
    total_journal = journal.total_debits # total billable = total receivable
    assert total_expense == total_journal
    # assert there is no fx gain account created
    gain_entries = [
        entry for entry in journal.entries 
        if entry.acct.acct_id == SystemAcctNumber.FX_GAIN
    ]
    assert len(gain_entries) == 0
    
    # test different currency expense
    journal = ExpenseService.create_journal_from_expense(sample_expense_rent)
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.EXPENSE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # total amount from expense should be same to total amount from journal (base currency)
    total_expense = FxService.convert(
        amount=sample_expense_rent.total, # total expense
        src_currency=sample_expense_rent.currency, # expense currency
        cur_dt=sample_expense_rent.expense_dt, # convert fx at expense date
    )
    total_journal = journal.total_debits # total billable = total receivable
    assert math.isclose(total_expense, total_journal, rel_tol=1e-6)
    # assert there is fx gain account created
    gain_entries = [
        entry for entry in journal.entries 
        if entry.acct.acct_id == SystemAcctNumber.FX_GAIN
    ]
    assert len(gain_entries) == 1
    gain_entry = gain_entries[0]
    assert math.isclose(gain_entry.amount_base, gain_entry.amount, rel_tol=1e-6)
    # calculate gain amount
    amount_expense = total_expense # in base amount
    amount_paid = FxService.convert(
        amount=sample_expense_rent.payment_amount, # paid in payment currency
        src_currency=AcctService.get_account(
            sample_expense_rent.payment_acct_id
        ).currency, # payment currency
        cur_dt=sample_expense_rent.expense_dt, # convert fx at expense date
    ) # in base amount
    gain_ = amount_expense - amount_paid
    assert math.isclose(gain_entry.amount_base, gain_, rel_tol=1e-6)
    
    

@mock.patch("src.app.dao.connection.get_engine")
def test_validate_expense(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.expense import ExpenseService
    
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
    
    # validate payment account id
    expense.payment_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        ExpenseService._validate_expense(expense)
    expense.payment_acct_id = 'acct-credit'
    # validate exp account id
    expense.expense_items[0].expense_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        ExpenseService._validate_expense(expense)
    expense.expense_items[0].expense_acct_id = 'acct-meal'
    # validate payment amount not match
    expense.payment_amount = 150
    with pytest.raises(NotMatchWithSystemError):
        # account not exist
        ExpenseService._validate_expense(expense)
    expense.payment_amount = 123.74
    
    # finally it should pass validation
    ExpenseService._validate_expense(expense)
    
@mock.patch("src.app.dao.connection.get_engine")
def test_expense(mock_engine, engine_with_sample_choa, sample_expense_meal, sample_expense_rent):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.expense import ExpenseService
    from src.app.service.journal import JournalService
    
    # test add expense
    ExpenseService.add_expense(sample_expense_meal)
    with pytest.raises(AlreadyExistError):
        ExpenseService.add_expense(sample_expense_meal)
    ExpenseService.add_expense(sample_expense_rent)
    
    # assert journal is correctly added
    _expense, _journal = ExpenseService.get_expense_journal(sample_expense_meal.expense_id)
    assert _expense == sample_expense_meal
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    _expense, _journal = ExpenseService.get_expense_journal(sample_expense_rent.expense_id)
    assert _expense == sample_expense_rent
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        ExpenseService.get_expense_journal('random-expense')
        
    # test list expenses
    expenses = ExpenseService.list_expense()
    assert len(expenses) == 2
    expenses = ExpenseService.list_expense(max_amount=1000)
    assert len(expenses) == 1
    expenses = ExpenseService.list_expense(min_amount=1300)
    assert len(expenses) == 1
    expenses = ExpenseService.list_expense(currency=CurType.EUR)
    assert len(expenses) == 1
    expenses = ExpenseService.list_expense(has_receipt=True)
    assert len(expenses) == 1
    
    # test update expense
    _invoice, _journal = ExpenseService.get_expense_journal(sample_expense_meal.expense_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    ## update1 -- valid expense level update
    sample_expense_meal.expense_dt = date(2024, 1, 2)
    sample_expense_meal.expense_items[1].amount_pre_tax -= 10
    sample_expense_meal.payment_amount -= 10
    ExpenseService.update_expense(sample_expense_meal)
    _expense, _journal = ExpenseService.get_expense_journal(sample_expense_meal.expense_id)
    assert _expense == sample_expense_meal
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
        
    # test delete expense
    with pytest.raises(NotExistError):
        ExpenseService.delete_expense('random-expense')
    ExpenseService.delete_expense(sample_expense_meal.expense_id)
    with pytest.raises(NotExistError):
        ExpenseService.get_expense_journal(sample_expense_meal.expense_id)
    ExpenseService.delete_expense(sample_expense_rent.expense_id)
    with pytest.raises(NotExistError):
        ExpenseService.get_expense_journal(sample_expense_rent.expense_id)
    