from datetime import date
import logging
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import CurType, EntityType, EntryType
from src.app.model.invoice import _InvoiceBalance, _InvoiceBrief, InvoiceItem, GeneralInvoiceItem, Item, Invoice
from src.app.dao.orm import EntityORM, InvoiceItemORM, GeneralInvoiceItemORM, InvoiceORM, ItemORM, EntryORM, PaymentItemORM, PaymentORM, infer_integrity_error
from src.app.dao.connection import get_engine
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, FKNoDeleteUpdateError


class itemDao:
    @classmethod
    def fromItem(cls, item: Item) -> ItemORM:
        return ItemORM.model_validate(
            item.model_dump()
        )
        
    @classmethod
    def toItem(cls, item_orm: ItemORM) -> Item:
        return Item.model_validate(
            item_orm.model_dump()
        )
        
    @classmethod
    def add(cls, item: Item):
        item_orm = cls.fromItem(item)
        with Session(get_engine()) as s:
            s.add(item_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(details=str(e))
            else:
                logging.info(f"Added {item_orm} to Item table")
        
        
    @classmethod
    def remove(cls, item_id: str):
        with Session(get_engine()) as s:
            sql = select(ItemORM).where(ItemORM.item_id == item_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(details=str(e))
            logging.info(f"Removed {p} from Item table")
        
        
    @classmethod
    def update(cls, item: Item):
        item_orm = cls.fromItem(item)
        with Session(get_engine()) as s:
            sql = select(ItemORM).where(
                ItemORM.item_id == item_orm.item_id
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            p.name = item_orm.name
            p.item_type = item_orm.item_type
            p.entity_type = item_orm.entity_type
            p.unit = item_orm.unit
            p.unit_price = item_orm.unit_price
            p.currency = item_orm.currency
            p.default_acct_id = item_orm.default_acct_id # TODO: only income/expense account
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
            logging.info(f"Updated to {p} from Item table")
        
        
    @classmethod
    def get(cls, item_id: str) -> Item:
        with Session(get_engine()) as s:
            sql = select(ItemORM).where(
                ItemORM.item_id == item_id
            )
            try:
                p = s.exec(sql).one() # get the item
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return cls.toItem(p)
    
    @classmethod
    def list_item(cls, entity_type: EntityType) -> list[Item]:
        with Session(get_engine()) as s:
            sql = select(ItemORM).where(ItemORM.entity_type == entity_type)
            item_orms = s.exec(sql).all()
        
        return [cls.toItem(item_orm) for item_orm in item_orms]


class invoiceDao:
    @classmethod
    def fromInvoiceItem(cls, invoice_id: str, invoice_item: InvoiceItem) -> InvoiceItemORM:
        return InvoiceItemORM(
            invoice_item_id=invoice_item.invoice_item_id,
            invoice_id=invoice_id,
            item_id=invoice_item.item.item_id,
            acct_id=invoice_item.acct_id,
            quantity=invoice_item.quantity,
            tax_rate=invoice_item.tax_rate,
            discount_rate=invoice_item.discount_rate,
            description=invoice_item.description,
        )
        
    @classmethod
    def fromGeneralInvoiceItem(cls, invoice_id: str, general_invoice_item: GeneralInvoiceItem) -> GeneralInvoiceItemORM:
        return GeneralInvoiceItemORM(
            ginv_item_id=general_invoice_item.ginv_item_id,
            invoice_id=invoice_id,
            incur_dt=general_invoice_item.incur_dt,
            acct_id=general_invoice_item.acct_id,
            currency=general_invoice_item.currency,
            amount_pre_tax_raw=general_invoice_item.amount_pre_tax_raw,
            amount_pre_tax=general_invoice_item.amount_pre_tax,
            tax_rate=general_invoice_item.tax_rate,
            description=general_invoice_item.description,
        )
        
    @classmethod
    def toInvoiceItem(cls, invoice_item_orm: InvoiceItemORM) -> InvoiceItem:
        return InvoiceItem(
            invoice_item_id=invoice_item_orm.invoice_item_id,
            item=itemDao.get(item_id=invoice_item_orm.item_id),
            quantity=invoice_item_orm.quantity,
            acct_id=invoice_item_orm.acct_id,
            tax_rate=invoice_item_orm.tax_rate,
            discount_rate=invoice_item_orm.discount_rate,
            description=invoice_item_orm.description,
        )
        
    @classmethod
    def toGeneralInvoiceItem(cls, general_invoice_item_orm: GeneralInvoiceItemORM) -> GeneralInvoiceItem:
        return GeneralInvoiceItem(
            ginv_item_id=general_invoice_item_orm.ginv_item_id,
            incur_dt=general_invoice_item_orm.incur_dt,
            acct_id=general_invoice_item_orm.acct_id,
            currency=general_invoice_item_orm.currency,
            amount_pre_tax_raw=general_invoice_item_orm.amount_pre_tax_raw,
            amount_pre_tax=general_invoice_item_orm.amount_pre_tax,
            tax_rate=general_invoice_item_orm.tax_rate,
            description=general_invoice_item_orm.description,
        )
        
    @classmethod
    def fromInvoice(cls, journal_id: str, invoice: Invoice) -> InvoiceORM:
        return InvoiceORM(
            invoice_id=invoice.invoice_id,
            invoice_num=invoice.invoice_num,
            invoice_dt=invoice.invoice_dt,
            due_dt=invoice.due_dt,
            entity_id=invoice.entity_id,
            entity_type=invoice.entity_type,
            subject=invoice.subject,
            currency=invoice.currency,
            shipping=invoice.shipping,
            note=invoice.note,
            journal_id=journal_id # TODO
        )
        
    @classmethod
    def toInvoice(
        cls, 
        invoice_orm: InvoiceORM, 
        invoice_item_orms: list[InvoiceItemORM],
        ginvoice_item_orms: list[GeneralInvoiceItemORM]
    ) -> Invoice:
        return Invoice(
            invoice_id=invoice_orm.invoice_id,
            invoice_num=invoice_orm.invoice_num,
            invoice_dt=invoice_orm.invoice_dt,
            due_dt=invoice_orm.due_dt,
            entity_id=invoice_orm.entity_id,
            entity_type=invoice_orm.entity_type,
            subject=invoice_orm.subject,
            currency=invoice_orm.currency,
            invoice_items=[
                cls.toInvoiceItem(invoice_item_orm) 
                for invoice_item_orm in invoice_item_orms  
            ],
            ginvoice_items=[
                cls.toGeneralInvoiceItem(ginvoice_item_orm) 
                for ginvoice_item_orm in ginvoice_item_orms  
            ],
            shipping=invoice_orm.shipping,
            note=invoice_orm.note,
        )
    
    @classmethod
    def add(cls, journal_id: str, invoice: Invoice):
        with Session(get_engine()) as s:
            # add invoice first
            invoice_orm = cls.fromInvoice(journal_id, invoice)
            
            s.add(invoice_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
            logging.info(f"Added {invoice_orm} to invoice table")
            
            # add invoice items
            for invoice_item in invoice.invoice_items:
                invoice_item_orm = cls.fromInvoiceItem(
                    invoice_id=invoice.invoice_id,
                    invoice_item=invoice_item
                )
                s.add(invoice_item_orm)
                logging.info(f"Added {invoice_item_orm} to invoice Item table")
                
            # add general invoice items
            for ginvoice_item in invoice.ginvoice_items:
                general_invoice_item_orm = cls.fromGeneralInvoiceItem(
                    invoice_id=invoice.invoice_id,
                    general_invoice_item=ginvoice_item
                )
                s.add(general_invoice_item_orm)
                logging.info(f"Added {general_invoice_item_orm} to general invoice Item table")
            
            # commit all items
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
            
    @classmethod
    def remove(cls, invoice_id: str):
        # only remove invoice, not journal, journal will be removed in journalDao
        with Session(get_engine()) as s:
            try:
                # remove invoice items first
                sql = delete(InvoiceItemORM).where(
                    InvoiceItemORM.invoice_id == invoice_id
                )
                s.exec(sql)
                # remove general invoice items next
                sql = delete(GeneralInvoiceItemORM).where(
                    GeneralInvoiceItemORM.invoice_id == invoice_id
                )
                s.exec(sql)
                
                # remove invoice
                sql = delete(InvoiceORM).where(
                    InvoiceORM.invoice_id == invoice_id
                )
                s.exec(sql)
                
                # commit at same time
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=False)
            
            logging.info(f"deleted invoice and items for {invoice_id}")
            
    @classmethod
    def update(cls, journal_id: str, invoice: Invoice):
        # journal_id is the new journal created first before calling this API
        # update invoice first
        with Session(get_engine()) as s:
            sql = select(InvoiceORM).where(
                InvoiceORM.invoice_id == invoice.invoice_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))

            # update
            invoice_orm = cls.fromInvoice(
                journal_id=journal_id,
                invoice=invoice
            )
            # must update invoice orm because journal id changed
            p.invoice_num = invoice_orm.invoice_num
            p.invoice_dt = invoice_orm.invoice_dt
            p.due_dt = invoice_orm.due_dt
            p.entity_id = invoice_orm.entity_id
            p.entity_type = invoice_orm.entity_type
            p.subject = invoice_orm.subject
            p.currency = invoice_orm.currency
            p.shipping = invoice_orm.shipping
            p.journal_id = journal_id # update to new journal id
            p.note = invoice_orm.note
            
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
                
            # remove existing invoice items
            sql = delete(InvoiceItemORM).where(
                InvoiceItemORM.invoice_id == invoice.invoice_id
            )
            s.exec(sql)
            
            # add new invoice items
            # add individual invoice items
            for invoice_item in invoice.invoice_items:
                invoice_item_orm = cls.fromInvoiceItem(
                    invoice_id=invoice.invoice_id,
                    invoice_item=invoice_item
                )
                s.add(invoice_item_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback() # will rollback both item removal and new item add
                raise FKNotExistError(
                    details=str(e)
                )
            
            # remove existing general invoice items
            sql = delete(GeneralInvoiceItemORM).where(
                GeneralInvoiceItemORM.invoice_id == invoice.invoice_id
            )
            s.exec(sql)
            # add new general invoice items
            # add individual invoice items
            for ginvoice_item in invoice.ginvoice_items:
                general_invoice_item_orm = cls.fromGeneralInvoiceItem(
                    invoice_id=invoice.invoice_id,
                    general_invoice_item=ginvoice_item
                )
                s.add(general_invoice_item_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback() # will rollback both item removal and new item add
                raise FKNotExistError(
                    details=str(e)
                )
            
    @classmethod
    def get(cls, invoice_id: str) -> Tuple[Invoice, str]:
        # return both invoice id and journal id
        with Session(get_engine()) as s:
            # get invoice items
            sql = select(InvoiceItemORM).where(
                InvoiceItemORM.invoice_id == invoice_id
            )
            try:
                invoice_item_orms = s.exec(sql).all()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # get general invoice items
            sql = select(GeneralInvoiceItemORM).where(
                GeneralInvoiceItemORM.invoice_id == invoice_id
            )
            try:
                ginvoice_item_orms = s.exec(sql).all()
            except NoResultFound as e:
                raise NotExistError(details=str(e))

            # get invoice
            sql = select(InvoiceORM).where(
                InvoiceORM.invoice_id == invoice_id
            )
            try:
                invoice_orm = s.exec(sql).one() # get the invoice
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            invoice = cls.toInvoice(
                invoice_orm=invoice_orm,
                invoice_item_orms=invoice_item_orms,
                ginvoice_item_orms=ginvoice_item_orms
            )
            jrn_id = invoice_orm.journal_id
        return invoice, jrn_id
    
    @classmethod
    def list_invoice(
        cls,
        limit: int = 50,
        offset: int = 0,
        entity_type: EntityType = EntityType.CUSTOMER,
        invoice_ids: list[str] | None = None,
        invoice_nums: list[str] | None = None,
        entity_ids: list[str] | None = None,
        entity_names: list[str] | None = None,
        is_business: bool | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31), 
        subject_keyword: str = '',
        currency: CurType | None = None,
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_invoice_items: int | None = None
    ) -> list[_InvoiceBrief]:
        with Session(get_engine()) as s:
            inv_filters = [
                InvoiceORM.invoice_dt.between(min_dt, max_dt), 
                InvoiceORM.subject.contains(subject_keyword),
                InvoiceORM.entity_type == entity_type
            ]
            if invoice_ids is not None:
                inv_filters.append(InvoiceORM.invoice_id.in_(invoice_ids))
            if invoice_nums is not None:
                inv_filters.append(InvoiceORM.invoice_num.in_(invoice_nums))
                
                
            invoice_item_agg = (
                select(
                    InvoiceItemORM.invoice_id,
                    #f.max(ItemORM.currency).label('currency'), # bug that only support min/max
                    f.count(InvoiceItemORM.invoice_item_id).label('num_invoice_items'),
                    f.sum(
                        InvoiceItemORM.quantity 
                        * ItemORM.unit_price 
                        * (1 - InvoiceItemORM.discount_rate) 
                        * (1 + InvoiceItemORM.tax_rate)
                    ).label('total_raw_amount')
                )
                .join(
                    ItemORM, 
                    onclause=InvoiceItemORM.item_id == ItemORM.item_id, 
                    isouter=False
                )
                .group_by(
                    InvoiceItemORM.invoice_id,
                    #ItemORM.currency
                )
                .subquery()
            )
            ginvoice_item_agg = (
                select(
                    GeneralInvoiceItemORM.invoice_id,
                    f.count(GeneralInvoiceItemORM.ginv_item_id).label('num_ginvoice_items'),
                    f.sum(
                        GeneralInvoiceItemORM.amount_pre_tax 
                        * (1 + GeneralInvoiceItemORM.tax_rate)
                    ).label('total_raw_amount')
                )
                .group_by(
                    GeneralInvoiceItemORM.invoice_id,
                    #ItemORM.currency
                )
                .subquery()
            )
            journal_summary = (
                select(
                    EntryORM.journal_id,
                    f.sum(EntryORM.amount_base).label('amount_base')
                )
                .where(
                    EntryORM.entry_type == EntryType.DEBIT
                )
                .group_by(
                    EntryORM.journal_id
                )
                .subquery()
            )
            # add currency filter
            if currency is not None:
                inv_filters.append(InvoiceORM.currency == currency)
            # add num items filter
            if num_invoice_items is not None:
                inv_filters.append(f.coalesce(invoice_item_agg.c.num_invoice_items, 0) == num_invoice_items)
            # add amount filter (raw amount):
            inv_filters.append(
                journal_summary.c.amount_base
                .between(min_amount, max_amount)
            )
            # add entity filter
            if entity_ids is not None:
                inv_filters.append(InvoiceORM.entity_id.in_(entity_ids))
            if entity_names is not None:
                inv_filters.append(EntityORM.entity_name.in_(entity_names))
            if is_business is not None:
                inv_filters.append(EntityORM.is_business == True)
            
            invoice_joined = (
                select(
                    InvoiceORM.invoice_id,
                    InvoiceORM.invoice_num,
                    InvoiceORM.invoice_dt,
                    EntityORM.entity_name,
                    EntityORM.is_business,
                    InvoiceORM.subject,
                    InvoiceORM.currency,
                    (
                        f.coalesce(invoice_item_agg.c.num_invoice_items, 0)
                        + f.coalesce(ginvoice_item_agg.c.num_ginvoice_items, 0)
                    ).label('num_invoice_items'),
                    (
                        InvoiceORM.shipping 
                        + f.coalesce(invoice_item_agg.c.total_raw_amount , 0)
                        + f.coalesce(ginvoice_item_agg.c.total_raw_amount, 0)
                    ).label('total_raw_amount'),
                    journal_summary.c.amount_base.label('total_base_amount')
                )
                .join(
                    EntityORM,
                    onclause=InvoiceORM.entity_id == EntityORM.entity_id, 
                    isouter=True # outer join
                )
                .join(
                    invoice_item_agg,
                    onclause=InvoiceORM.invoice_id  == invoice_item_agg.c.invoice_id, 
                    isouter=True # use left join bc there is chance that an invoice does not have item
                )
                .join(
                    ginvoice_item_agg,
                    onclause=InvoiceORM.invoice_id  == ginvoice_item_agg.c.invoice_id, 
                    isouter=True # use left join bc there is chance that an invoice does not have general item
                )
                .join(
                    journal_summary,
                    onclause=InvoiceORM.journal_id  == journal_summary.c.journal_id, 
                    isouter=False
                )
                .where(
                    *inv_filters
                )
                .order_by(InvoiceORM.invoice_dt.desc(), InvoiceORM.invoice_id)
                .offset(offset)
                .limit(limit)
            )
            
            try:
                invoices = s.exec(invoice_joined).all()
            except NoResultFound as e:
                return []
            
        return [
            _InvoiceBrief(
                invoice_id=invoice.invoice_id,
                invoice_num=invoice.invoice_num,
                invoice_dt=invoice.invoice_dt,
                entity_name=invoice.entity_name,
                entity_type=entity_type,
                is_business=invoice.is_business,
                subject=invoice.subject,
                currency=invoice.currency,
                num_invoice_items=invoice.num_invoice_items,
                total_raw_amount=invoice.total_raw_amount,
                total_base_amount=invoice.total_base_amount,
            ) 
            for invoice in invoices
        ]
        
    @classmethod
    def get_invoice_balance(cls, invoice_id: str, bal_dt: date) -> _InvoiceBalance:
        with Session(get_engine()) as s:
            invoice_item_agg = (
                select(
                    f.sum(
                        InvoiceItemORM.quantity 
                        * ItemORM.unit_price 
                        * (1 - InvoiceItemORM.discount_rate) 
                        * (1 + InvoiceItemORM.tax_rate)
                    ).label('total_raw_amount')
                )
                .join(
                    ItemORM, 
                    onclause=InvoiceItemORM.item_id == ItemORM.item_id, 
                    isouter=False # inner join
                )
                .where(
                    InvoiceItemORM.invoice_id == invoice_id,
                )
                .subquery()
            )
            ginvoice_item_agg = (
                select(
                    f.sum(
                        GeneralInvoiceItemORM.amount_pre_tax 
                        * (1 + GeneralInvoiceItemORM.tax_rate)
                    ).label('total_raw_amount')
                )
                .where(
                    GeneralInvoiceItemORM.invoice_id == invoice_id,
                )
                .subquery()
            )
            payment_agg = (
                select(
                    f.sum(PaymentItemORM.payment_amount_raw).label('payment_amount_raw')
                )
                .join(
                    PaymentORM, 
                    onclause=PaymentItemORM.payment_id == PaymentORM.payment_id, 
                    isouter=False # inner join
                )
                .where(
                    PaymentItemORM.invoice_id == invoice_id,
                    PaymentORM.payment_dt <= bal_dt # only look at payment before given date
                )
                .subquery()
            )
            
            invoice_joined = (
                select(
                    InvoiceORM.currency,
                    InvoiceORM.invoice_num,
                    (
                        InvoiceORM.shipping 
                        + f.coalesce(invoice_item_agg.c.total_raw_amount , 0)
                        + f.coalesce(ginvoice_item_agg.c.total_raw_amount, 0)
                    ).label('total_raw_amount'),
                    f.coalesce(payment_agg.c.payment_amount_raw , 0).label('payment_amount_raw')
                )
                .where(
                    InvoiceORM.invoice_id == invoice_id,
                )
            )
            
            try:
                joined = s.exec(invoice_joined).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return _InvoiceBalance(
            invoice_id=invoice_id,
            invoice_num=joined.invoice_num,
            currency=joined.currency,
            raw_amount=joined.total_raw_amount,
            paid_amount=joined.payment_amount_raw
        )
        
    @classmethod
    def get_invoices_balance_by_entity(cls, entity_id: str, bal_dt: date) -> list[_InvoiceBalance]:
        with Session(get_engine()) as s:
            invoice_item_agg = (
                select(
                    InvoiceItemORM.invoice_id,
                    f.sum(
                        InvoiceItemORM.quantity 
                        * ItemORM.unit_price 
                        * (1 - InvoiceItemORM.discount_rate) 
                        * (1 + InvoiceItemORM.tax_rate)
                    ).label('total_raw_amount')
                )
                .join(
                    ItemORM, 
                    onclause=InvoiceItemORM.item_id == ItemORM.item_id, 
                    isouter=False # inner join
                )
                .group_by(
                    InvoiceItemORM.invoice_id
                )
                .subquery()
            )
            ginvoice_item_agg = (
                select(
                    GeneralInvoiceItemORM.invoice_id,
                    f.sum(
                        GeneralInvoiceItemORM.amount_pre_tax 
                        * (1 + GeneralInvoiceItemORM.tax_rate)
                    ).label('total_raw_amount')
                )
                .group_by(
                    GeneralInvoiceItemORM.invoice_id
                )
                .subquery()
            )
            payment_agg = (
                select(
                    PaymentItemORM.invoice_id,
                    f.sum(PaymentItemORM.payment_amount_raw).label('payment_amount_raw')
                )
                .join(
                    PaymentORM, 
                    onclause=PaymentItemORM.payment_id == PaymentORM.payment_id, 
                    isouter=False # inner join
                )
                .where(
                    PaymentORM.payment_dt <= bal_dt # only look at payment before given date
                )
                .group_by(
                    PaymentItemORM.invoice_id
                )
                .subquery()
            )
            
            invoice_joined = (
                select(
                    InvoiceORM.invoice_id,
                    InvoiceORM.invoice_num,
                    InvoiceORM.currency,
                    (
                        InvoiceORM.shipping 
                        + f.coalesce(invoice_item_agg.c.total_raw_amount , 0)
                        + f.coalesce(ginvoice_item_agg.c.total_raw_amount, 0)
                    ).label('total_raw_amount'),
                    f.coalesce(payment_agg.c.payment_amount_raw , 0).label('payment_amount_raw')
                )
                .join(
                    invoice_item_agg, 
                    onclause=invoice_item_agg.c.invoice_id == InvoiceORM.invoice_id, 
                    isouter=True # left join
                )
                .join(
                    ginvoice_item_agg, 
                    onclause=ginvoice_item_agg.c.invoice_id == InvoiceORM.invoice_id, 
                    isouter=True # left join
                )
                .join(
                    payment_agg, 
                    onclause=payment_agg.c.invoice_id == InvoiceORM.invoice_id, 
                    isouter=True # left join
                )
                .where(
                    InvoiceORM.entity_id == entity_id,
                )
            )
            
            try:
                joined = s.exec(invoice_joined).all()
            except NoResultFound as e:
                return []
            
        return [
            _InvoiceBalance(
                invoice_id=j.invoice_id,
                invoice_num=j.invoice_num,
                currency=j.currency,
                raw_amount=j.total_raw_amount,
                paid_amount=j.payment_amount_raw
            ) 
            for j in joined
        ]