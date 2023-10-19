import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from model.accounts import BalSh, IncExp
from dao.acct import acctBalshDao, acctIncExpDao

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