from legacy.model.accounts import BalSh, IncExp
from legacy.dao.acct import acctBalshDao, acctIncExpDao

class AcctManager:
    @classmethod
    def createBalsh(cls, acct: BalSh):
        acctBalshDao.add(acct)
        
    @classmethod
    def updateBalsh(cls, acct: BalSh):
        acctBalshDao.update(acct)
        
    @classmethod
    def deleteBalsh(cls, acct_id: str):
        acctBalshDao.remove(acct_id=acct_id)
        
    @classmethod
    def createIncExp(cls, acct: IncExp):
        acctIncExpDao.add(acct)
        
    @classmethod
    def updateIncExp(cls, acct: IncExp):
        acctIncExpDao.update(acct)
        
    @classmethod
    def deleteIncExp(cls, acct_id: str):
        acctIncExpDao.remove(acct_id=acct_id)