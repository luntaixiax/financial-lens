from datetime import date
import logging
import math
import pytest
from unittest import mock
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import CurType, ItemType, JournalSrc, UnitType
from src.app.model.expense import Expense, ExpenseItem, ExpInfo, Merchant
from src.app.model.const import SystemAcctNumber

def test_create_journal_from_expense(
    session_with_sample_choa, 
    sample_expense_meal, 
    sample_expense_rent, 
    test_expense_service, 
    test_fx_service, 
    test_acct_service
):
    
    # test same currency expense
    journal = test_expense_service.create_journal_from_expense(sample_expense_meal)
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.EXPENSE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # total amount from expense should be same to total amount from journal (base currency)
    total_expense = test_fx_service.convert_to_base(
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
    journal = test_expense_service.create_journal_from_expense(sample_expense_rent)
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.EXPENSE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # total amount from expense should be same to total amount from journal (base currency)
    total_expense = test_fx_service.convert_to_base(
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
    amount_paid = test_fx_service.convert_to_base(
        amount=sample_expense_rent.payment_amount, # paid in payment currency
        src_currency=test_acct_service.get_account(
            sample_expense_rent.payment_acct_id
        ).currency, # payment currency
        cur_dt=sample_expense_rent.expense_dt, # convert fx at expense date
    ) # in base amount
    gain_ = amount_expense - amount_paid
    assert math.isclose(gain_entry.amount_base, gain_, rel_tol=1e-6)
    
    
def test_validate_expense(session_with_sample_choa, test_expense_service, test_setting_service):
    
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
        payment_acct_id='acct-credit', # same currency
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
    
    # validate payment account id
    expense.payment_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_expense_service._validate_expense(expense)
    expense.payment_acct_id = 'acct-credit'
    # validate exp account id
    expense.expense_items[0].expense_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_expense_service._validate_expense(expense)
    expense.expense_items[0].expense_acct_id = 'acct-meal'
    # validate payment amount not match
    expense.payment_amount = 150
    with pytest.raises(NotMatchWithSystemError):
        # account not exist
        test_expense_service._validate_expense(expense)
    expense.payment_amount = 123.74
    
    # finally it should pass validation
    test_expense_service._validate_expense(expense)
    
def test_expense(session_with_sample_choa, sample_expense_meal, sample_expense_rent, 
                test_expense_service, test_journal_service):
    
    # test add expense
    test_expense_service.add_expense(sample_expense_meal)
    with pytest.raises(AlreadyExistError):
        test_expense_service.add_expense(sample_expense_meal)
    test_expense_service.add_expense(sample_expense_rent)
    
    # assert journal is correctly added
    _expense, _journal = test_expense_service.get_expense_journal(sample_expense_meal.expense_id)
    assert _expense == sample_expense_meal
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    _expense, _journal = test_expense_service.get_expense_journal(sample_expense_rent.expense_id)
    assert _expense == sample_expense_rent
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        test_expense_service.get_expense_journal('random-expense')
        
    # test list expenses
    expenses, _ = test_expense_service.list_expense()
    assert len(expenses) == 2
    expenses, _ = test_expense_service.list_expense(max_amount=1000)
    assert len(expenses) == 1
    expenses, _ = test_expense_service.list_expense(min_amount=1300)
    assert len(expenses) == 1
    expenses, _ = test_expense_service.list_expense(currency=CurType.EUR)
    assert len(expenses) == 1
    expenses, _ = test_expense_service.list_expense(has_receipt=True)
    assert len(expenses) == 1
    expenses, _ = test_expense_service.list_expense(expense_acct_ids=['acct-meal'])
    assert len(expenses) == 1
    expenses, _ = test_expense_service.list_expense(expense_acct_ids=['acct-rental'])
    assert len(expenses) == 1
    
    # test update expense
    _invoice, _journal = test_expense_service.get_expense_journal(sample_expense_meal.expense_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    ## update1 -- valid expense level update
    sample_expense_meal.expense_dt = date(2024, 1, 2)
    sample_expense_meal.expense_items[1].amount_pre_tax -= 10
    sample_expense_meal.payment_amount -= 10
    test_expense_service.update_expense(sample_expense_meal)
    _expense, _journal = test_expense_service.get_expense_journal(sample_expense_meal.expense_id)
    assert _expense == sample_expense_meal
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
        
    # test delete expense
    with pytest.raises(NotExistError):
        test_expense_service.delete_expense('random-expense')
    test_expense_service.delete_expense(sample_expense_meal.expense_id)
    with pytest.raises(NotExistError):
        test_expense_service.get_expense_journal(sample_expense_meal.expense_id)
    test_expense_service.delete_expense(sample_expense_rent.expense_id)
    with pytest.raises(NotExistError):
        test_expense_service.get_expense_journal(sample_expense_rent.expense_id)
    