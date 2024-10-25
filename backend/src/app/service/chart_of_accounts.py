
from src.app.dao.accounts import acctDao, bankAcctDao
from src.app.model.accounts import Account, BankAccount


def add_account(acct: Account):
    acctDao.add(acct)
    
def add_bank_account(acct: BankAccount):
    acctDao.add(acct)
    bankAcctDao.add(acct.acct_id, acct)
    
def get_account(acct_id: str) -> Account:
    return acctDao.get(acct_id=acct_id)

def get_bank_account(acct_id: str) -> BankAccount:
    bank_acct = bankAcctDao.get(linked_acct_id=acct_id)
    acct = acctDao.get(acct_id=acct_id)
    bank = BankAccount(
        acct_id=acct.acct_id,
        acct_name=acct.acct_name,
        acct_type=acct.acct_type,
        currency=acct.currency,
        is_group=acct.is_group,
        parent_acct_id=acct.parent_acct_id,
        bank_account=bank_acct,
    )
    return bank