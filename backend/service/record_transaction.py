import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from model.transactions import Transaction
from model.enums import EntryType
from dao.transaction import entryDao, transactionDao
from dao.acct import acctBalshDao

class TransManager:
    @classmethod
    def checkEntriesBalance(cls, transaction: Transaction) -> bool:
        # check debit credit balance
        balance_summary = dict()
        for entry in transaction.entries:
            if entry.acct_id_balsh is not None:
                # it is an account transation
                acct = acctBalshDao.get(acct_id=entry.acct_id_balsh)
                currency = acct.currency
            else:
                currency = entry.incexp_cur
            
            if currency not in balance_summary:
                balance_summary[currency] = {
                    EntryType.DEBIT : entry.amount if entry.entry_type == EntryType.DEBIT else 0,
                    EntryType.CREDIT : entry.amount if entry.entry_type == EntryType.CREDIT else 0,
                }
            else:
                balance_summary[currency][entry.entry_type] += entry.amount
        
        if len(balance_summary) > 1:
            # multiple currency transaction
            # TODO: check FX rate
            print("Multi Currency Transaction, coming soon!")
        else:
            bal = balance_summary[currency] # use last currency
            if bal[EntryType.DEBIT] != bal[EntryType.CREDIT]:
                print(f"Debit({bal[EntryType.DEBIT]}) and Credit({bal[EntryType.CREDIT]}) not equal")
                return False
            
            return True
    
    @classmethod
    def create(cls, transaction: Transaction):
        if cls.checkEntriesBalance(transaction = transaction):
            transactionDao.add(transaction)
            for entry in transaction.entries:
                entryDao.add(
                    trans_id = transaction.trans_id,
                    entry = entry
                )
        else:
            raise ValueError("Debit/Credit amount not reconcile")
    
    @classmethod
    def update(cls, transaction: Transaction):
        if cls.checkEntriesBalance(transaction = transaction):
            transactionDao.update(transaction)
            
            # check existing entry, if there are any not in the new transaction object
            # if any, need to delete
            new_entry_ids = [entry.entry_id for entry in transaction.entries]
            for exist_entry in entryDao.gets(trans_id=transaction.trans_id):
                if exist_entry.entry_id not in new_entry_ids:
                    entryDao.remove(entry_id = exist_entry.entry_id)
            
            # check new entries
            existing_entry_ids = entryDao.get_entry_ids(trans_id=transaction.trans_id)
            for entry in transaction.entries:
                if entry.entry_id in existing_entry_ids:
                    # if entry is an existing one, update it
                    entryDao.update(
                        entry = entry
                    )
                else:
                    # if entry does not exist, create it
                    entryDao.add(
                        trans_id = transaction.trans_id,
                        entry = entry
                    )
                    
            
        else:
            raise ValueError("Debit/Credit amount not reconcile")
    
    @classmethod
    def get(cls, trans_id: str) -> Transaction:
        trans = transactionDao.get(trans_id = trans_id) # no entries
        trans.entries = entryDao.gets(transid = trans_id)
        return trans
    
    @classmethod
    def delete(cls, trans_id: str):
        entries = entryDao.gets(trans_id = trans_id)
        for entry in entries:
            entryDao.remove(entry_id = entry.entry_id)
        transactionDao.remove(trans_id = trans_id)