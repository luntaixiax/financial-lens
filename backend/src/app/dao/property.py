
from datetime import date
import logging
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import PropertyTransactionType, PropertyType
from src.app.dao.orm import PropertyORM, PropertyTransactionORM, infer_integrity_error
from src.app.model.property import Property, PropertyTransaction, _PropertyPriceBrief
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, FKNoDeleteUpdateError
from src.app.dao.connection import get_engine

class propertyDao:
    @classmethod
    def fromProperty(cls, journal_id: str, property: Property) -> PropertyORM:
        return PropertyORM(
            property_id=property.property_id,
            property_name=property.property_name,
            property_type=property.property_type,
            pur_dt=property.pur_dt,
            pur_price=property.pur_price,
            tax=property.tax,
            pur_acct_id=property.pur_acct_id,
            journal_id=journal_id,
        )
        
    @classmethod
    def toProperty(cls, property_orm: PropertyORM) -> Property:
        return Property(
            property_id=property_orm.property_id,
            property_name=property_orm.property_name,
            property_type=property_orm.property_type,
            pur_dt=property_orm.pur_dt,
            tax=property_orm.tax,
            pur_price=property_orm.pur_price,
            pur_acct_id=property_orm.pur_acct_id,
        )
        
    @classmethod
    def add(cls, journal_id: str, property: Property):
        with Session(get_engine()) as s:
            property_orm = cls.fromProperty(journal_id, property)
        s.add(property_orm)
        try:
            s.commit()
        except IntegrityError as e:
            s.rollback()
            raise infer_integrity_error(e, during_creation=True)
        logging.info(f"Added {property_orm} to property table")
        
    @classmethod
    def remove(cls, property_id: str):
        # remove property
        with Session(get_engine()) as s:
            sql = delete(PropertyORM).where(
                PropertyORM.property_id == property_id
            )
            
            # commit at same time
            try:
                s.exec(sql)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(str(e))
            logging.info(f"deleted property for {property_id}")
            
    @classmethod
    def get(cls, property_id: str) -> Tuple[Property, str]:
        # return both property id and journal id
        with Session(get_engine()) as s:

            # get property
            sql = select(PropertyORM).where(
                PropertyORM.property_id == property_id
            )
            try:
                property_orm = s.exec(sql).one() # get the property
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            property = cls.toProperty(
                property_orm=property_orm,
            )
            jrn_id = property_orm.journal_id
        return property, jrn_id
    
    @classmethod
    def update(cls, journal_id: str, property: Property):
        with Session(get_engine()) as s:
            sql = select(PropertyORM).where(
                PropertyORM.property_id == property.property_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            property_orm = cls.fromProperty(
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
            p.journal_id = journal_id # update to new journal id
            
            try:
                s.add(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNotExistError(
                    details=str(e)
                )
            else:
                s.refresh(p) # update p to instantly have new values
                
    @classmethod
    def list_properties(cls) -> list[Property]:
        with Session(get_engine()) as s:

            # get property
            sql = select(PropertyORM)
            try:
                property_orms = s.exec(sql).all() # get the property
            except NoResultFound as e:
                return []
            
            properties = [cls.toProperty(
                property_orm=property_orm,
            ) for property_orm in property_orms]
            
        return properties
                
                
class propertyTransactionDao:
    @classmethod
    def fromPropertyTrans(cls, journal_id: str, property_trans: PropertyTransaction) -> PropertyTransactionORM:
        return PropertyTransactionORM(
            trans_id=property_trans.trans_id,
            property_id=property_trans.property_id,
            trans_dt=property_trans.trans_dt,
            trans_type=property_trans.trans_type,
            trans_amount=property_trans.trans_amount,
            journal_id=journal_id,
        )
        
    @classmethod
    def toPropertyTrans(cls, property_trans_orm: PropertyTransactionORM) -> PropertyTransaction:
        return PropertyTransaction(
            trans_id=property_trans_orm.trans_id,
            property_id=property_trans_orm.property_id,
            trans_dt=property_trans_orm.trans_dt,
            trans_type=property_trans_orm.trans_type,
            trans_amount=property_trans_orm.trans_amount,
        )
        
    @classmethod
    def add(cls, journal_id: str, property_trans: PropertyTransaction):
        with Session(get_engine()) as s:
            property_trans_orm = cls.fromPropertyTrans(journal_id, property_trans)
            
            s.add(property_trans_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
            logging.info(f"Added {property_trans_orm} to property transaction table")
        
    @classmethod
    def remove(cls, trans_id: str):
        # remove property
        with Session(get_engine()) as s:
            sql = delete(PropertyTransactionORM).where(
                PropertyTransactionORM.trans_id == trans_id
            )
            
            # commit at same time
            try:
                s.exec(sql)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(str(e))
            logging.info(f"deleted property transaction for {trans_id}")
            
    @classmethod
    def get(cls, trans_id: str) -> Tuple[PropertyTransaction, str]:
        # return both property id and journal id
        with Session(get_engine()) as s:

            # get property transactions
            sql = select(PropertyTransactionORM).where(
                PropertyTransactionORM.trans_id == trans_id
            )
            try:
                property_trans_orm = s.exec(sql).one() # get the property
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            property_trans = cls.toPropertyTrans(
                property_trans_orm=property_trans_orm,
            )
            jrn_id = property_trans_orm.journal_id
        return property_trans, jrn_id
    
    @classmethod
    def update(cls, journal_id: str, property_trans: PropertyTransaction):
        with Session(get_engine()) as s:
            sql = select(PropertyTransactionORM).where(
                PropertyTransactionORM.trans_id == property_trans.trans_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            property_trans_orm = cls.fromPropertyTrans(
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
                s.add(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNotExistError(
                    details=str(e)
                )
            else:
                s.refresh(p) # update p to instantly have new values
                
    @classmethod
    def get_acc_stat(cls, property_id: str, rep_dt: date) -> _PropertyPriceBrief:
        with Session(get_engine()) as s:
            prop_summary = (
                select(PropertyORM)
                .where(
                    PropertyORM.pur_dt <= rep_dt,
                    PropertyORM.property_id == property_id,   
                )
            )
            try:
                prop = s.exec(prop_summary).one()
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
                result = s.exec(flow_summary).all()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            
            prop = propertyDao.toProperty(prop)
            p = _PropertyPriceBrief(pur_cost=prop.pur_cost)
            if len(result) > 0:
                attr_mapping = {
                    PropertyTransactionType.APPRECIATION: 'acc_depreciation',
                    PropertyTransactionType.DEPRECIATION: 'acc_appreciation',
                    PropertyTransactionType.IMPAIRMENT: 'acc_impairment',
                }
                for r in result:
                    setattr(p, attr_mapping.get(r.trans_type), r.acc_amount)
                
        return p
                
    
    @classmethod
    def list_transactions(cls, property_id: str) -> list[PropertyTransaction]:
        with Session(get_engine()) as s:

            # get property transactions
            sql = select(PropertyTransactionORM).where(
                PropertyTransactionORM.property_id == property_id
            )
            try:
                property_trans_orms = s.exec(sql).all() # get the property
            except NoResultFound as e:
                return []
            
            property_trans = [cls.toPropertyTrans(
                property_trans_orm=property_trans_orm,
            ) for property_trans_orm in property_trans_orms]
            
        return property_trans
    
    
        