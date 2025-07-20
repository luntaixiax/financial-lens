
from datetime import date
import logging
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import PropertyTransactionType, PropertyType
from src.app.dao.orm import PropertyORM, PropertyTransactionORM, infer_integrity_error
from src.app.model.property import Property, PropertyTransaction, _PropertyPriceBrief
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, FKNoDeleteUpdateError
from src.app.dao.connection import UserDaoAccess

class propertyDao:
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
        
    def fromProperty(self, journal_id: str, property: Property) -> PropertyORM:
        return PropertyORM(
            property_id=property.property_id,
            property_name=property.property_name,
            property_type=property.property_type,
            pur_dt=property.pur_dt,
            pur_price=property.pur_price,
            tax=property.tax,
            pur_acct_id=property.pur_acct_id,
            note=property.note,
            receipts=property.receipts,
            journal_id=journal_id,
        )
        
    def toProperty(self, property_orm: PropertyORM) -> Property:
        if property_orm.receipts == 'null':
            property_orm.receipts = None
        return Property(
            property_id=property_orm.property_id,
            property_name=property_orm.property_name,
            property_type=property_orm.property_type,
            pur_dt=property_orm.pur_dt,
            tax=property_orm.tax,
            pur_price=property_orm.pur_price,
            pur_acct_id=property_orm.pur_acct_id,
            receipts=property_orm.receipts,
            note=property_orm.note
        )

    def add(self, journal_id: str, property: Property):
        property_orm = self.fromProperty(journal_id, property)
        self.dao_access.user_session.add(property_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
    def remove(self, property_id: str):
        # remove property
        sql = delete(PropertyORM).where(
            PropertyORM.property_id == property_id
        )
        
        # commit at same time
        try:
            self.dao_access.user_session.exec(sql) # type: ignore
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNoDeleteUpdateError(str(e))
            
    def get(self, property_id: str) -> Tuple[Property, str]:
        # return both property id and journal id
        # get property
        sql = select(PropertyORM).where(
            PropertyORM.property_id == property_id
        )
        try:
            property_orm = self.dao_access.user_session.exec(sql).one() # get the property
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        property = self.toProperty(
            property_orm=property_orm,
        )
        jrn_id = property_orm.journal_id
        return property, jrn_id
    
    def update(self, journal_id: str, property: Property):
        sql = select(PropertyORM).where(
            PropertyORM.property_id == property.property_id,
        )
        try:
            p = self.dao_access.user_session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        property_orm = self.fromProperty(
            journal_id=journal_id,
            property=property
        )
        # must update property orm because journal id changed
        p.property_name = property_orm.property_name
        p.property_type = property_orm.property_type
        p.pur_dt = property_orm.pur_dt
        p.pur_price = property_orm.pur_price
        p.tax = property_orm.tax
        p.pur_acct_id = property_orm.pur_acct_id
        p.note = property_orm.note
        p.receipts = property_orm.receipts
        p.journal_id = journal_id # update to new journal id
        
        try:
            self.dao_access.user_session.add(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNotExistError(
                details=str(e)
            )
        else:
            self.dao_access.user_session.refresh(p) # update p to instantly have new values
                
    def list_properties(self) -> list[Property]:
        # get property
        sql = select(PropertyORM)
        try:
            property_orms = self.dao_access.user_session.exec(sql).all() # get the property
        except NoResultFound as e:
            return []
        
        properties = [self.toProperty(
            property_orm=property_orm,
        ) for property_orm in property_orms]
            
        return properties
                
                
class propertyTransactionDao:
    def __init__(self, dao_access: UserDaoAccess):  
        self.dao_access = dao_access
        
    def fromPropertyTrans(self, journal_id: str, property_trans: PropertyTransaction) -> PropertyTransactionORM:
        return PropertyTransactionORM(
            trans_id=property_trans.trans_id,
            property_id=property_trans.property_id,
            trans_dt=property_trans.trans_dt,
            trans_type=property_trans.trans_type,
            trans_amount=property_trans.trans_amount,
            journal_id=journal_id,
        )
        
    def toPropertyTrans(self, property_trans_orm: PropertyTransactionORM) -> PropertyTransaction:
        return PropertyTransaction(
            trans_id=property_trans_orm.trans_id,
            property_id=property_trans_orm.property_id,
            trans_dt=property_trans_orm.trans_dt,
            trans_type=property_trans_orm.trans_type,
            trans_amount=property_trans_orm.trans_amount,
        )
        
    def add(self, journal_id: str, property_trans: PropertyTransaction):
        property_trans_orm = self.fromPropertyTrans(journal_id, property_trans)
            
        self.dao_access.user_session.add(property_trans_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
    def remove(self, trans_id: str):
        # remove property
            sql = delete(PropertyTransactionORM).where(
                PropertyTransactionORM.trans_id == trans_id
            )
            
            # commit at same time
            try:
                self.dao_access.user_session.exec(sql) # type: ignore
                self.dao_access.user_session.commit()
            except IntegrityError as e:
                self.dao_access.user_session.rollback()
                raise FKNoDeleteUpdateError(str(e))
            
    def get(self, trans_id: str) -> Tuple[PropertyTransaction, str]:
        # return both property id and journal id

        # get property transactions
        sql = select(PropertyTransactionORM).where(
            PropertyTransactionORM.trans_id == trans_id
        )
        try:
            property_trans_orm = self.dao_access.user_session.exec(sql).one() # get the property
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        property_trans = self.toPropertyTrans(
            property_trans_orm=property_trans_orm,
        )
        jrn_id = property_trans_orm.journal_id
        return property_trans, jrn_id
    
    def update(self, journal_id: str, property_trans: PropertyTransaction):
        sql = select(PropertyTransactionORM).where(
            PropertyTransactionORM.trans_id == property_trans.trans_id,
        )
        try:
            p = self.dao_access.user_session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        property_trans_orm = self.fromPropertyTrans(
            journal_id=journal_id,
            property_trans=property_trans
        )
        # must update property orm because journal id changed
        p.property_id = property_trans_orm.property_id
        p.trans_dt = property_trans_orm.trans_dt
        p.trans_type = property_trans_orm.trans_type
        p.trans_amount = property_trans_orm.trans_amount
        p.journal_id = journal_id # update to new journal id
        
        try:
            self.dao_access.user_session.add(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNotExistError(
                details=str(e)
            )
        else:
            self.dao_access.user_session.refresh(p) # update p to instantly have new values
                
    def get_acc_stat(self, property_id: str, rep_dt: date) -> _PropertyPriceBrief:
        prop_summary = (
            select(PropertyORM)
            .where(
                PropertyORM.pur_dt <= rep_dt,
                PropertyORM.property_id == property_id,   
            )
        )
        try:
            prop = self.dao_access.user_session.exec(prop_summary).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        flow_summary = (
            select(
                PropertyTransactionORM.trans_type,
                f.sum(PropertyTransactionORM.trans_amount).label('acc_amount')
            )
            .where(
                PropertyTransactionORM.property_id == property_id,
                PropertyTransactionORM.trans_dt <= rep_dt,
            )
            .group_by(
                PropertyTransactionORM.trans_type,
            )
        )

        try:
            result = self.dao_access.user_session.exec(flow_summary).all()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        
        prop = propertyDao(self.dao_access).toProperty(prop)
        p = _PropertyPriceBrief(pur_cost=prop.pur_cost) # type: ignore
        if len(result) > 0:
            attr_mapping = {
                PropertyTransactionType.APPRECIATION: 'acc_depreciation',
                PropertyTransactionType.DEPRECIATION: 'acc_appreciation',
                PropertyTransactionType.IMPAIRMENT: 'acc_impairment',
            }
            for r in result:
                setattr(p, attr_mapping.get(r.trans_type), r.acc_amount) # type: ignore
                
        return p
                
    
    def list_transactions(self, property_id: str) -> list[PropertyTransaction]:
        # get property transactions
        sql = select(PropertyTransactionORM).where(
            PropertyTransactionORM.property_id == property_id
        )
        try:
            property_trans_orms = self.dao_access.user_session.exec(sql).all() # get the property
        except NoResultFound as e:
            return []
        
        property_trans = [self.toPropertyTrans(
            property_trans_orm=property_trans_orm,
        ) for property_trans_orm in property_trans_orms]
            
        return property_trans
    
    
        