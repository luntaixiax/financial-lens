from datetime import date
import logging
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.dao.orm import PaymentItemORM, PaymentORM, infer_integrity_error
from src.app.model.payment import Payment, PaymentItem
from src.app.dao.connection import get_engine


class paymentDao:
    
    @classmethod
    def fromPaymentItem(cls, payment_id: str, payment_item: PaymentItem) -> PaymentItemORM:
        return PaymentItemORM(
            payment_item_id=payment_item.payment_item_id,
            payment_id=payment_id,
            invoice_id=payment_item.invoice_id,
            payment_amount=payment_item.payment_amount,
            payment_amount_raw=payment_item.payment_amount_raw,
        )
        
    @classmethod
    def toPaymentItem(cls, payment_item_orm: PaymentItemORM) -> PaymentItem:
        return PaymentItem(
            payment_item_id=payment_item_orm.payment_item_id,
            invoice_id=payment_item_orm.invoice_id,
            payment_amount=payment_item_orm.payment_amount,
            payment_amount_raw=payment_item_orm.payment_amount_raw,
        )
    
    @classmethod
    def fromPayment(cls, journal_id: str, payment: Payment) -> PaymentORM:
        return PaymentORM(
            payment_id=payment.payment_id,
            payment_num=payment.payment_num,
            payment_dt=payment.payment_dt,
            entity_type=payment.entity_type,
            payment_acct_id=payment.payment_acct_id,
            journal_id=journal_id, # use pre-inserted journal id
            payment_fee=payment.payment_fee,
            ref_num=payment.ref_num,
            note=payment.note
        )
        
    @classmethod
    def toPayment(cls, payment_orm: PaymentORM, payment_item_orms: list[PaymentItemORM]) -> Payment:
        return Payment(
            payment_id=payment_orm.payment_id,
            payment_num=payment_orm.payment_num,
            payment_dt=payment_orm.payment_dt,
            entity_type=payment_orm.entity_type,
            payment_items=[
                cls.toPaymentItem(payment_item_orm) 
                for payment_item_orm in payment_item_orms
            ],
            payment_acct_id=payment_orm.payment_acct_id,
            payment_fee=payment_orm.payment_fee,
            ref_num=payment_orm.ref_num,
            note=payment_orm.note
        )
    
    @classmethod
    def add(cls, journal_id: str, payment: Payment):
        with Session(get_engine()) as s:
            # add payment first
            payment_orm = cls.fromPayment(journal_id=journal_id, payment=payment)
            s.add(payment_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(details=str(e))
            else:
                logging.info(f"Added {payment_orm} to Payment table")
            
            # add individual payment items
            for payment_item in payment.payment_items:
                payment_item_orm = cls.fromPaymentItem(
                    payment_id=payment.payment_id,
                    payment_item=payment_item
                )
                s.add(payment_item_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                # remove payment as well
                s.delete(payment_orm)
                s.commit()
                raise infer_integrity_error(e, during_creation=True)
            else:
                logging.info(f"Added {payment_item_orm} to Payment Item table")
        
    @classmethod
    def get(cls, payment_id: str) -> Payment:
        with Session(get_engine()) as s:
            # get payment items
            sql = select(PaymentItemORM).where(
                PaymentItemORM.payment_id == payment_id
            )
            try:
                payment_item_orms = s.exec(sql).all()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            # get payment
            sql = select(PaymentORM).where(
                PaymentORM.payment_id == payment_id
            )
            try:
                payment_orm = s.exec(sql).one() # get the payment
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            payment = cls.toPayment(
                payment_orm=payment_orm,
                payment_item_orms=payment_item_orms
            )
            
        return payment
            
    @classmethod
    def remove(cls, payment_id: str):
        with Session(get_engine()) as s:
            # remove payment items
            sql = delete(PaymentItemORM).where(
                PaymentItemORM.payment_id == payment_id
            )
            s.exec(sql)
            # remove payment
            sql = select(PaymentORM).where(
                PaymentORM.payment_id == payment_id
            )
            p = s.exec(sql).one()
            
            # commit at same time
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=False)
            logging.info(f"deleted payment and payment items for {payment_id}")
            
    @classmethod
    def update(cls, journal_id: str, payment: Payment):
        # update payment
        with Session(get_engine()) as s:
            sql = select(PaymentORM).where(
                PaymentORM.payment_id == payment.payment_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            payment_orm = cls.fromPayment(
                journal_id=journal_id, 
                payment=payment
            )
            if not p == payment_orm:
                p.payment_num = payment_orm.payment_num
                p.payment_dt = payment_orm.payment_dt
                p.entity_type = payment_orm.entity_type
                p.payment_acct_id = payment_orm.payment_acct_id
                p.payment_fee = payment_orm.payment_fee
                p.ref_num = payment_orm.ref_num
                p.note = payment_orm.note
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
        
            # remove existing payment items
            sql = delete(PaymentItemORM).where(
                PaymentItemORM.payment_id == payment.payment_id
            )
            s.exec(sql)
            
            # add new payment items
            # add individual payment items
            for payment_item in payment.payment_items:
                payment_item_orm = cls.fromPaymentItem(
                    payment_id=payment.payment_id,
                    payment_item=payment_item
                )
                s.add(payment_item_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback() # will rollback both item removal and new item add
                raise FKNotExistError(
                    details=str(e)
                )