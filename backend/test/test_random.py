from datetime import date

from src.app.service.chart_of_accounts import get_bank_account
from src.app.dao.fx import fxDao
from src.app.dao.orm import SQLModel
from src.app.dao.connection import engine
from src.app.model.entity import *
from src.app.model.enums import *
from src.app.model.accounts import *
from src.app.dao.accounts import *
from src.app.dao.journal import *
from src.app.model.journal import *

#SQLModel.metadata.create_all(engine)



# entry - normal case
# entry1 = Entry(
#     entry_type=EntryType.DEBIT,
#     acct=acctDao.get('acct-8a9c96fd'),
#     amount=55,
#     amount_base=55,
#     description='Meal'
# )
# entry2 = Entry(
#     entry_type=EntryType.DEBIT,
#     acct=acctDao.get('acct-043dcff7'),
#     amount=5,
#     amount_base=5
# )
# entry3 = Entry(
#     entry_type=EntryType.CREDIT,
#     acct=get_bank_account('acct-519be5c2'),
#     amount=50, # original amount
#     amount_base=60
# )
# journal = journalDao.get(journal_id = 'jrn-2cd6845f-39b7')
# journal.entries = [
#     entry1,
#     entry2,
#     entry3
# ]
# journal.jrn_date = date(2024, 10, 1)
# journalDao.update(journal)

def test_save_chart_of_accounts(sample_chart_of_accounts):
    for choa in sample_chart_of_accounts.values():
        chartOfAcctDao.save(choa)

    
    # save accounts
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
    acctDao.add(acct_expense)
    acctDao.add(acct_tax)
    acctDao.add(acct_bank)
    bankAcctDao.add(acct_bank.acct_id, acct_bank.bank_account)

