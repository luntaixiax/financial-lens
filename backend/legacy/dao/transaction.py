import logging
from typing import Dict, List
from dacite import from_dict, Config
from enum import Enum
from dataclasses import asdict
from sqlmodel import Session, select
from legacy.dao.orm import EntryORM, TransactionORM
from legacy.dao.connection import engine
from legacy.model.transactions import Entry, Transaction
from legacy.utils.exceptions import DuplicateEntryError

class entryDao:
    @classmethod
    def fromEntry(cls, trans_id: str, entry: Entry) -> EntryORM:
        return EntryORM(
            trans_id = trans_id,
            **asdict(entry)
        )
        
    @classmethod
    def toEntry(cls, entry_orm: EntryORM) -> Entry:
        entry_dict = entry_orm.dict()
        del entry_dict['trans_id']
        
        return from_dict(
            data_class = Entry,
            data = entry_dict,
            config = Config(cast = [Enum])
        )
        
    @classmethod
    def add(cls, trans_id: str, entry: Entry):
        entry_orm = cls.fromEntry(trans_id = trans_id, entry = entry)
        with Session(engine) as s:
            s.add(entry_orm)
            s.commit()
            logging.info(f"Added {entry_orm} to Entry table")
            
    @classmethod
    def remove(cls, entry_id: str):
        with Session(engine) as s:
            sql = select(EntryORM).where(EntryORM.entry_id == entry_id)
            p = s.exec(sql).one() # get the entry
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Entry table")
        
    @classmethod
    def update(cls, entry: Entry):
        entry_orm = cls.fromEntry(trans_id = '[temp]', entry = entry)
        with Session(engine) as s:
            sql = select(EntryORM).where(EntryORM.entry_id == entry_orm.entry_id)
            p = s.exec(sql).one() # get the entry
            
            # update
            p.entry_type = entry_orm.entry_type
            p.acct_id_balsh = entry_orm.acct_id_balsh
            p.acct_id_incexp = entry_orm.acct_id_incexp
            p.incexp_cur = entry_orm.incexp_cur
            p.amount = entry_orm.amount
            p.event = entry_orm.event
            p.project = entry_orm.project
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Account table")
        
    @classmethod
    def get(cls, entry_id: str) -> Entry:
        with Session(engine) as s:
            sql = select(EntryORM).where(EntryORM.entry_id == entry_id)
            p = s.exec(sql).one() # get the account
        return cls.toEntry(p)
    
    @classmethod
    def gets(cls, trans_id: str) -> List[Entry]:
        with Session(engine) as s:
            sql = select(EntryORM).where(EntryORM.trans_id == trans_id)
            ps = s.exec(sql).all() # get the account
        return [cls.toEntry(p) for p in ps]
    
    @classmethod
    def get_entry_ids(cls, trans_id: str) -> List[str]:
        with Session(engine) as s:
            sql = select(EntryORM.entry_id).where(EntryORM.trans_id == trans_id)
            ids = s.exec(sql).all() # get the account
        return ids
        

class transactionDao:
    # this will not append any entries
    @classmethod
    def fromTransaction(cls, trans: Transaction) -> TransactionORM:
        trans_dict = asdict(trans)
        del trans_dict['entries']
        return TransactionORM(
            **trans_dict
        )
        
    @classmethod
    def toTransaction(cls, trans_orm: TransactionORM) -> Transaction:
        return from_dict(
            data_class = Transaction,
            data = trans_orm,
            config = Config(cast = [Enum])
        )
        
    @classmethod
    def add(cls, trans: Transaction):
        trans_orm = cls.fromTransaction(trans = trans)
        with Session(engine) as s:
            s.add(trans_orm)
            s.commit()
            logging.info(f"Added {trans_orm} to Transaction table")
            
    @classmethod
    def remove(cls, trans_id: str):
        with Session(engine) as s:
            sql = select(TransactionORM).where(TransactionORM.trans_id == trans_id)
            p = s.exec(sql).one() # get the transaction
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Transaction table")
        
    @classmethod
    def update(cls, trans: Transaction):
        trans_orm = cls.fromTransaction(trans = trans)
        with Session(engine) as s:
            sql = select(TransactionORM).where(TransactionORM.trans_id == trans_orm.trans_id)
            p = s.exec(sql).one() # get the transaction
            
            # update
            p.trans_dt = trans_orm.trans_dt
            p.entity_id = trans_orm.entity_id
            p.note = trans_orm.note
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Transaction table")
        
    @classmethod
    def get(cls, trans_id: str) -> Transaction:
        # note there is no entry appended
        with Session(engine) as s:
            sql = select(TransactionORM).where(TransactionORM.trans_id == trans_id)
            p = s.exec(sql).one() # get the transaction
        return cls.toTransaction(p)
    
    
if __name__ == '__main__':
    pass