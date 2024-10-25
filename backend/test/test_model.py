import pytest
from pydantic import BaseModel, ValidationError
from src.app.model.entity import *
from src.app.model.enums import *
from src.app.model.accounts import *
from src.app.model.journal import *


def test_account(sample_chart_of_accounts: dict[AcctType, ChartNode]):
    # test if error raised for missing currency for balance sheet account
    with pytest.raises(ValidationError):
        a = Account(
            acct_name="BMO Checking",
            acct_type=AcctType.AST,
            currency=None,
            chart=sample_chart_of_accounts[AcctType.AST].find_node(
                '1110 - Bank'
            ).chart
        )
    
    # test if error raised for assign currency for income statement account
    with pytest.raises(ValidationError):
        r = Account(
            acct_name="Revenue",
            acct_type=AcctType.INC,
            currency=CurType.CAD,
            chart=sample_chart_of_accounts[AcctType.INC].find_node(
                '4100 - General Income'
            ).chart
        )
        
    b = Account(
        acct_name="Meal",
        acct_type=AcctType.EXP,
        currency=None,
        chart=sample_chart_of_accounts[AcctType.EXP].find_node(
            '5200 - Meals and Entertainment'
        ).chart
    )
    # test error raised if add currency to income statement account
    with pytest.raises(ValidationError):
        b.currency = CurType.USD
        

def test_bank_account_creation(sample_chart_of_accounts: dict[AcctType, ChartNode]):
    b = BankAccount(
        acct_name="BMO Checking",
        currency=CurType.CAD,
        chart=sample_chart_of_accounts[AcctType.AST].find_node(
            '1110 - Bank'
        ).chart,
        bank_account=BankAcct(
            bank_name="BMO",
            bank_acct_number="1254",
            bank_acct_type=BankAcctType.SAV
        )
    )
    # test cannot assign wrong bank account type
    with pytest.raises(ValidationError):
        b.bank_account=BankAcct(
            bank_name="BMO",
            bank_acct_number="1254",
            bank_acct_type=BankAcctType.CREDIT # cannot assign wrong type
        )
    # test cannot change bank account attributes on the fly
    with pytest.raises(ValidationError):
        b.bank_account.bank_acct_type = BankAcctType.CREDIT

def test_customer_creation():
    # test ship address automatically created if ship_same_as_bill=True
    c = Customer(
        customer_name = 'LTX Company',
        is_business=True,
        default_bill_curreny=CurType.CAD,
        bill_contact=Contact(
            name='luntaixia',
            email='infodesk@ltxservice.ca',
            phone='123456789',
            address=Address(
                address1='00 XX St E',
                suite_no=1234,
                city='Toronto',
                state='ON',
                country='Canada',
                postal_code='XYZABC'
            )
        ),
        ship_same_as_bill=True
    )
    assert c.ship_contact == c.bill_contact
    
    # test ship address be overwrite to bill address if ship_same_as_bill=True
    c = Customer(
        customer_name = 'LTX Company',
        is_business=True,
        default_bill_curreny=CurType.CAD,
        bill_contact=Contact(
            name='luntaixia',
            email='infodesk@ltxservice.ca',
            phone='123456789',
            address=Address(
                address1='00 XX St E',
                suite_no=1234,
                city='Toronto',
                state='ON',
                country='Canada',
                postal_code='XYZABC'
            )
        ),
        ship_contact=Contact(
            name='luntaixia2',
            email='infodesk2@ltxservice.ca',
            phone='987654321',
            address=Address(
                address1='00 XX St E',
                suite_no=1234,
                city='Toronto',
                state='ON',
                country='Canada',
                postal_code='XYZABC'
            )
        ),
        ship_same_as_bill=True
    )
    assert c.ship_contact == c.bill_contact
    

def test_journal_entry_base_currency(sample_chart_of_accounts: dict[AcctType, ChartNode]):
    acct_expense = Account(
        acct_name="Meal",
        acct_type=AcctType.EXP,
        currency=None,
        chart=sample_chart_of_accounts[AcctType.EXP].find_node(
            '5200 - Meals and Entertainment'
        ).chart
    )
    acct_tax = Account(
        acct_name="Input Tax",
        acct_type=AcctType.AST,
        currency=CurType.CAD,
        chart=sample_chart_of_accounts[AcctType.AST].find_node(
            '1200 - Non-Current Asset'
        ).chart
    )
    acct_bank = BankAccount(
        acct_name="BMO Checking",
        currency=CurType.CAD,
        chart=sample_chart_of_accounts[AcctType.AST].find_node(
            '1110 - Bank'
        ).chart,
        bank_account=BankAcct(
            bank_name="BMO",
            bank_acct_number="1254",
            bank_acct_type=BankAcctType.SAV
        )
    )
    
    # entry - amount not equal case
    with pytest.raises(ValidationError):
        entry1 = Entry(
            entry_type=EntryType.DEBIT,
            acct=acct_expense,
            amount=57.5,
            amount_base=20,
            description='Meal'
        )
    
    # journal entry - normal case
    entry1 = Entry(
        entry_type=EntryType.DEBIT,
        acct=acct_expense,
        amount=57.5,
        amount_base=57.5,
        description='Meal'
    )
    entry2 = Entry(
        entry_type=EntryType.DEBIT,
        acct=acct_tax,
        amount=2.5,
        amount_base=2.5
    )
    entry3 = Entry(
        entry_type=EntryType.CREDIT,
        acct=acct_bank,
        amount=60,
        amount_base=60
    )
    journal = Journal(
        jrn_date=date(2024, 1, 1),
        entries=[
            entry1,
            entry2,
            entry3
        ],
        note="buy lunch"
    )
    
    # journal entry - imbalance case
    entry4 = Entry(
        entry_type=EntryType.CREDIT,
        acct=acct_bank,
        amount=65,
        amount_base=65
    )
    with pytest.raises(ValidationError):
        
        journal = Journal(
            jrn_date=date(2024, 1, 1),
            entries=[
                entry1,
                entry2,
                entry4
            ],
            note="buy lunch"
        )
    

def test_journal_entry_multi_currency(sample_chart_of_accounts: dict[AcctType, ChartNode]):
    
    acct_expense = Account(
        acct_name="Meal",
        acct_type=AcctType.EXP,
        currency=None,
        chart=sample_chart_of_accounts[AcctType.EXP].find_node(
            '5200 - Meals and Entertainment'
        ).chart
    )
    acct_tax = Account(
        acct_name="Input Tax",
        acct_type=AcctType.AST,
        currency=CurType.CAD,
        chart=sample_chart_of_accounts[AcctType.AST].find_node(
            '1200 - Non-Current Asset'
        ).chart
    )
    acct_bank = BankAccount(
        acct_name="WISE USD",
        currency=CurType.USD,
        chart=sample_chart_of_accounts[AcctType.AST].find_node(
            '1110 - Bank'
        ).chart,
        bank_account=BankAcct(
            bank_name="Wise",
            bank_acct_number="1234",
            bank_acct_type=BankAcctType.SAV
        )
    )
    
    # entry - normal case
    entry1 = Entry(
        entry_type=EntryType.DEBIT,
        acct=acct_expense,
        amount=57.5,
        amount_base=57.5,
        description='Meal'
    )
    entry2 = Entry(
        entry_type=EntryType.DEBIT,
        acct=acct_tax,
        amount=2.5,
        amount_base=2.5
    )
    entry3 = Entry(
        entry_type=EntryType.CREDIT,
        acct=acct_bank,
        amount=45, # original amount
        amount_base=60
    )
    
    # journal entry - imbalance case
    entry4 = Entry(
        entry_type=EntryType.CREDIT,
        acct=acct_bank,
        amount=45,
        amount_base=63
    )
    with pytest.raises(ValidationError):
        
        journal = Journal(
            jrn_date=date(2024, 1, 1),
            entries=[
                entry1,
                entry2,
                entry4
            ],
            note="buy lunch"
        )