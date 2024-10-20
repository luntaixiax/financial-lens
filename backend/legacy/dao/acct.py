import logging
from typing import Dict, List
from dacite import from_dict, Config
from enum import Enum
from dataclasses import asdict
from sqlmodel import Session, select
from legacy.dao.orm import AcctBalshORM, AcctIncExpORM
from legacy.dao.connection import engine
from legacy.model.accounts import BalSh, IncExp
from legacy.utils.exceptions import DuplicateEntryError


class acctBalshDao:
    @classmethod
    def fromBalshAcct(cls, acct: BalSh) -> AcctBalshORM:
        return AcctBalshORM(
            **asdict(acct)
        )
        
    @classmethod
    def toBalshAcct(cls, acct_orm: AcctBalshORM) -> BalSh:
        return from_dict(
            data_class = BalSh,
            data = acct_orm.dict(),
            config = Config(cast = [Enum])
        )
        
    @classmethod
    def add(cls, acct: BalSh):
        acct_orm = cls.fromBalshAcct(acct)
        with Session(engine) as s:
            s.add(acct_orm)
            s.commit()
            logging.info(f"Added {acct_orm} to Account table")
            
    @classmethod
    def remove(cls, acct_id: str):
        with Session(engine) as s:
            sql = select(AcctBalshORM).where(AcctBalshORM.acct_id == acct_id)
            p = s.exec(sql).one() # get the ccount
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Account table")
        
    @classmethod
    def update(cls, acct: BalSh):
        acct_orm = cls.fromBalshAcct(acct)
        with Session(engine) as s:
            sql = select(AcctBalshORM).where(AcctBalshORM.acct_id == acct_orm.acct_id)
            p = s.exec(sql).one() # get the account
            
            # update
            p.acct_name = acct_orm.acct_name
            p.entity_id = acct_orm.entity_id
            p.acct_type = acct_orm.acct_type
            p.currency = acct_orm.currency
            p.accrual = acct_orm.accrual
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Account table")
        
    @classmethod
    def get(cls, acct_id: str) -> BalSh:
        with Session(engine) as s:
            sql = select(AcctBalshORM).where(AcctBalshORM.acct_id == acct_id)
            p = s.exec(sql).one() # get the account
        return cls.toBalshAcct(p)
        
        
class acctIncExpDao:
    @classmethod
    def fromIncExpAcct(cls, acct: IncExp) -> AcctIncExpORM:
        return AcctIncExpORM(
            **asdict(acct)
        )
        
    @classmethod
    def toIncExpAcct(cls, acct_orm: AcctIncExpORM) -> IncExp:
        return from_dict(
            data_class = IncExp,
            data = acct_orm.dict(),
            config = Config(cast = [Enum])
        )
        
    @classmethod
    def add(cls, acct:IncExp):
        acct_orm = cls.fromIncExpAcct(acct)
        with Session(engine) as s:
            s.add(acct_orm)
            s.commit()
            logging.info(f"Added {acct_orm} to Account table")
            
    @classmethod
    def remove(cls, acct_id: str):
        with Session(engine) as s:
            sql = select(AcctIncExpORM).where(AcctIncExpORM.acct_id == acct_id)
            p = s.exec(sql).one() # get the ccount
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Account table")
        
    @classmethod
    def update(cls, acct:IncExp):
        acct_orm = cls.fromIncExpAcct(acct)
        with Session(engine) as s:
            sql = select(AcctIncExpORM).where(AcctIncExpORM.acct_id == acct_orm.acct_id)
            p = s.exec(sql).one() # get the account
            
            # update
            p.acct_name = acct_orm.acct_name
            p.entity_id = acct_orm.entity_id
            p.acct_type = acct_orm.acct_type
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Account table")
        
    @classmethod
    def get(cls, acct_id: str) -> BalSh:
        with Session(engine) as s:
            sql = select(AcctIncExpORM).where(AcctIncExpORM.acct_id == acct_id)
            p = s.exec(sql).one() # get the account
        return cls.toIncExpAcct(p)
        
        
if __name__ == '__main__':
    print(acctBalshDao.get(acct_id='a-2a81cd'))