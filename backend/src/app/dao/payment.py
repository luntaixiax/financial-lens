from datetime import date
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.const import SystemAcctNumber
from src.app.model.enums import CurType, EntityType, EntryType
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.dao.orm import AcctORM, EntryORM, InvoiceORM, PaymentItemORM, PaymentORM, infer_integrity_error
from src.app.model.payment import Payment, PaymentItem, _PaymentBrief
from src.app.dao.connection import UserDaoAccess


class paymentDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
        
    def fromPaymentItem(self, payment_id: str, payment_item: PaymentItem) -> PaymentItemORM:
        return PaymentItemORM(
            payment_item_id=payment_item.payment_item_id,
            payment_id=payment_id,
            invoice_id=payment_item.invoice_id,
            payment_amount=payment_item.payment_amount,
            payment_amount_raw=payment_item.payment_amount_raw,
        )
        
    def toPaymentItem(self, payment_item_orm: PaymentItemORM) -> PaymentItem:
        return PaymentItem(
            payment_item_id=payment_item_orm.payment_item_id,
            invoice_id=payment_item_orm.invoice_id,
            payment_amount=payment_item_orm.payment_amount,
            payment_amount_raw=payment_item_orm.payment_amount_raw,
        )
    
    def fromPayment(self, journal_id: str, payment: Payment) -> PaymentORM:
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
        
    def toPayment(self, payment_orm: PaymentORM, payment_item_orms: list[PaymentItemORM]) -> Payment:
        return Payment(
            payment_id=payment_orm.payment_id,
            payment_num=payment_orm.payment_num,
            payment_dt=payment_orm.payment_dt,
            entity_type=payment_orm.entity_type,
            payment_items=[
                self.toPaymentItem(payment_item_orm) 
                for payment_item_orm in payment_item_orms
            ],
            payment_acct_id=payment_orm.payment_acct_id,
            payment_fee=payment_orm.payment_fee,
            ref_num=payment_orm.ref_num,
            note=payment_orm.note
        )
    
    def add(self, journal_id: str, payment: Payment):
        # add payment first
        payment_orm = self.fromPayment(journal_id=journal_id, payment=payment)
        self.dao_access.user_session.add(payment_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise AlreadyExistError(details=str(e))
        
        # add individual payment items
        for payment_item in payment.payment_items:
            payment_item_orm = self.fromPaymentItem(
                payment_id=payment.payment_id,
                payment_item=payment_item
            )
            self.dao_access.user_session.add(payment_item_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            # remove payment as well
            self.dao_access.user_session.delete(payment_orm)
            self.dao_access.user_session.commit()
            raise infer_integrity_error(e, during_creation=True)

        
    def get(self, payment_id: str) -> Tuple[Payment, str]:
        # get payment items
        sql = select(PaymentItemORM).where(
            PaymentItemORM.payment_id == payment_id
        )
        try:
            payment_item_orms = self.dao_access.user_session.exec(sql).all()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        # get payment
        sql = select(PaymentORM).where(
            PaymentORM.payment_id == payment_id
        )
        try:
            payment_orm = self.dao_access.user_session.exec(sql).one() # get the payment
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        payment = self.toPayment(
            payment_orm=payment_orm,
            payment_item_orms=payment_item_orms
        )
        jrn_id = payment_orm.journal_id
            
        return payment, jrn_id
            
    def remove(self, payment_id: str):
        # remove payment items
        sql = delete(PaymentItemORM).where(
            PaymentItemORM.payment_id == payment_id
        )
        self.dao_access.user_session.exec(sql) # type: ignore
        # remove payment
        sql = select(PaymentORM).where(
            PaymentORM.payment_id == payment_id
        )
        
        try:
            p = self.dao_access.user_session.exec(sql).one() # get the payment
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # commit at same time
        try:
            self.dao_access.user_session.delete(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=False)
            
    def update(self, journal_id: str, payment: Payment):
        # update payment
        sql = select(PaymentORM).where(
            PaymentORM.payment_id == payment.payment_id,
        )
        try:
            p = self.dao_access.user_session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        payment_orm = self.fromPayment(
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
                self.dao_access.user_session.add(p)
                self.dao_access.user_session.commit()
            except IntegrityError as e:
                self.dao_access.user_session.rollback()
                raise FKNotExistError(
                    details=str(e)
                )
            else:
                self.dao_access.user_session.refresh(p) # update p to instantly have new values
    
        # remove existing payment items
        sql = delete(PaymentItemORM).where(
            PaymentItemORM.payment_id == payment.payment_id
        )
        self.dao_access.user_session.exec(sql) # type: ignore
        
        # add new payment items
        # add individual payment items
        for payment_item in payment.payment_items:
            payment_item_orm = self.fromPaymentItem(
                payment_id=payment.payment_id,
                payment_item=payment_item
            )
            self.dao_access.user_session.add(payment_item_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback() # will rollback both item removal and new item add
            raise FKNotExistError(
                details=str(e)
            )
                
    def list_payment(
        self,
        limit: int = 50,
        offset: int = 0,
        entity_type: EntityType = EntityType.CUSTOMER,
        payment_ids: list[str] | None = None,
        payment_nums: list[str] | None = None,
        payment_acct_id: str | None = None,
        payment_acct_name: str | None = None,
        invoice_ids: list[str] | None = None,
        invoice_nums: list[str] | None = None,
        currency: CurType | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31),
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_invoices: int | None = None
    ) -> list[_PaymentBrief]:
        inv_case_when = []
        if invoice_ids is not None:
            inv_case_when.append(
                f.max(
                    case(
                        (InvoiceORM.invoice_id.in_(invoice_ids), 1), # type: ignore
                        else_=0
                    )
                ).label('contains_invoice_id'),
            )
        if invoice_nums is not None:
            inv_case_when.append(
                f.max(
                    case(
                        (InvoiceORM.invoice_num.in_(invoice_nums), 1), # type: ignore
                        else_=0
                    )
                ).label('contains_invoice_num')
            )
        payment_item_agg = (
            select(
                PaymentItemORM.payment_id,
                f.count(PaymentItemORM.invoice_id.distinct()).label('num_invoices'), # type: ignore
                # all payment items should use same currency to pay (so can sum across different items)
                f.sum(PaymentItemORM.payment_amount).label('payment_amount'), # in payment currency
                f.sum(PaymentItemORM.payment_amount_raw).label('payment_amount_raw'), # in invoice currency
                f.group_concat(InvoiceORM.invoice_num).label('invoice_num_strs'),
                *inv_case_when
            )
            .join(
                InvoiceORM,
                onclause=PaymentItemORM.invoice_id == InvoiceORM.invoice_id, 
                isouter=True # outer join
            )
            .group_by(
                PaymentItemORM.payment_id,
            )
            .subquery()
        )
        accrual_acct_id = SystemAcctNumber.ACCT_RECEIV if entity_type == EntityType.CUSTOMER else SystemAcctNumber.ACCT_PAYAB
        accrual_entry_type = EntryType.CREDIT if entity_type == EntityType.CUSTOMER else EntryType.DEBIT
        journal_summary = (
            select(
                EntryORM.journal_id,
                f.sum(EntryORM.amount_base).label('gross_payment_base'),
                f.sum(case(
                    (EntryORM.acct_id.in_((accrual_acct_id, )), EntryORM.amount_base), # type: ignore
                    else_=0
                )).label('accrual_offset_base'),
            )
            .where(
                EntryORM.entry_type == accrual_entry_type
            )
            .group_by(
                EntryORM.journal_id
            )
            .subquery()
        )
        
        pmt_filters = [
            PaymentORM.payment_dt.between(min_dt, max_dt), # type: ignore
            PaymentORM.entity_type == entity_type,
            journal_summary.c.gross_payment_base.between(min_amount, max_amount),
        ]
        # add payment currency filter
        if currency is not None:
            pmt_filters.append(AcctORM.currency == currency)
        if payment_acct_id is not None:
            pmt_filters.append(AcctORM.acct_id == payment_acct_id)
        if payment_acct_name is not None:
            pmt_filters.append(AcctORM.acct_name == payment_acct_name)
        # add num items filter
        if num_invoices is not None:
            pmt_filters.append(payment_item_agg.c.num_invoices == num_invoices)
        # add payment id filters
        if payment_ids is not None:
            pmt_filters.append(PaymentORM.payment_id.in_(payment_ids)) # type: ignore
        if payment_nums is not None:
            pmt_filters.append(PaymentORM.payment_num.in_(payment_nums)) # type: ignore
        if invoice_ids is not None:
            pmt_filters.append(payment_item_agg.c.contains_invoice_id == 1)
        if invoice_nums is not None:
            pmt_filters.append(payment_item_agg.c.contains_invoice_num == 1)
            
        joined = (
            select(
                PaymentORM.payment_id,
                PaymentORM.payment_num,
                PaymentORM.payment_dt,
                PaymentORM.entity_type,
                AcctORM.currency,
                AcctORM.acct_name.label('payment_acct_name'), # type: ignore
                payment_item_agg.c.num_invoices,
                payment_item_agg.c.payment_amount,
                payment_item_agg.c.invoice_num_strs,
                journal_summary.c.accrual_offset_base,
                journal_summary.c.gross_payment_base
            )
            .join(
                AcctORM,
                onclause=PaymentORM.payment_acct_id == AcctORM.acct_id, 
                isouter=True # outer join
            )
            .join(
                payment_item_agg,
                onclause=PaymentORM.payment_id == payment_item_agg.c.payment_id, 
                isouter=False # inner join
            )
            .join(
                journal_summary,
                onclause=PaymentORM.journal_id == journal_summary.c.journal_id, 
                isouter=False # inner join
            )
            .where(
                *pmt_filters
            )
            .order_by(PaymentORM.payment_dt.desc(), PaymentORM.payment_id) # type: ignore
            .offset(offset)
            .limit(limit)
        )
        
        try:
            payments = self.dao_access.user_session.exec(joined).all()
        except NoResultFound as e:
            return []
            
        return [
            _PaymentBrief(
                payment_id=payment.payment_id,
                payment_num=payment.payment_num,
                payment_dt=payment.payment_dt,
                entity_type=payment.entity_type,
                currency=payment.currency,
                payment_acct_name=payment.payment_acct_name,
                num_invoices=payment.num_invoices,
                invoice_num_strs=payment.invoice_num_strs,
                accrual_offset_base=payment.accrual_offset_base,
                gross_payment_base=payment.gross_payment_base, # in base currency
                gross_payment=payment.payment_amount # in payment currency
            )
            for payment in payments
        ]