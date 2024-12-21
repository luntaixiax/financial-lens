from datetime import date
import logging
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import CurType, EntryType
from src.app.model.invoice import _InvoiceBrief, InvoiceItem, Item, Invoice
from src.app.dao.orm import InvoiceItemORM, InvoiceORM, ItemORM, EntryORM, infer_integrity_error
from src.app.dao.connection import get_engine
from src.app.model.exceptions import AlreadyExistError, NotExistError, FKNoDeleteUpdateError


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
            except IntegrityError as e:
                raise FKNoDeleteUpdateError(details=str(e))
            
            s.delete(p)
            s.commit()
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
    def list(cls) -> list[Item]:
        with Session(get_engine()) as s:
            sql = select(ItemORM)
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
    def fromInvoice(cls, journal_id: str, invoice: Invoice) -> InvoiceORM:
        return InvoiceORM(
            invoice_id=invoice.invoice_id,
            invoice_num=invoice.invoice_num,
            invoice_dt=invoice.invoice_dt,
            due_dt=invoice.due_dt,
            customer_id=invoice.customer_id,
            subject=invoice.subject,
            currency=invoice.currency,
            shipping=invoice.shipping,
            note=invoice.note,
            journal_id=journal_id # TODO
        )
        
    @classmethod
    def toInvoice(cls, invoice_orm: InvoiceORM, invoice_item_orms: list[InvoiceItemORM]) -> Invoice:
        return Invoice(
            invoice_id=invoice_orm.invoice_id,
            invoice_num=invoice_orm.invoice_num,
            invoice_dt=invoice_orm.invoice_dt,
            due_dt=invoice_orm.due_dt,
            customer_id=invoice_orm.customer_id,
            subject=invoice_orm.subject,
            currency=invoice_orm.currency,
            invoice_items=[
                cls.toInvoiceItem(invoice_item_orm) 
                for invoice_item_orm in invoice_item_orms  
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
            # remove invoice items first
            sql = delete(InvoiceItemORM).where(
                InvoiceItemORM.invoice_id == invoice_id
            )
            s.exec(sql)
            # remove invoice
            sql = delete(InvoiceORM).where(
                InvoiceORM.invoice_id == invoice_id
            )
            s.exec(sql)
            
            # commit at same time
            s.commit()
            logging.info(f"deleted invoice and items for {invoice_id}")

            
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
                invoice_item_orms=invoice_item_orms
            )
            jrn_id = invoice_orm.journal_id
        return invoice, jrn_id
    
    @classmethod
    def list(
        cls,
        limit: int = 50,
        offset: int = 0,
        invoice_ids: list[str] | None = None,
        invoice_nums: list[str] | None = None,
        customer_ids: list[str] | None = None,
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
                InvoiceORM.subject.contains(subject_keyword)
            ]
            if invoice_ids is not None:
                inv_filters.append(InvoiceORM.invoice_id.in_(invoice_ids))
            if invoice_nums is not None:
                inv_filters.append(InvoiceORM.invoice_num.in_(invoice_nums))
            if customer_ids is not None:
                inv_filters.append(InvoiceORM.customer_id.in_(customer_ids))
                
                
            invoice_item_joined = (
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
                inv_filters.append(invoice_item_joined.c.num_invoice_items == num_invoice_items)
            # add amount filter (raw amount):
            inv_filters.append(
                journal_summary.c.amount_base
                .between(min_amount, max_amount)
            )
            invoice_joined = (
                select(
                    InvoiceORM.invoice_id,
                    InvoiceORM.invoice_num,
                    InvoiceORM.invoice_dt,
                    InvoiceORM.customer_id,
                    InvoiceORM.subject,
                    InvoiceORM.currency,
                    invoice_item_joined.c.num_invoice_items,
                    (InvoiceORM.shipping + invoice_item_joined.c.total_raw_amount).label('total_raw_amount'),
                    journal_summary.c.amount_base.label('total_base_amount')
                )
                .join(
                    invoice_item_joined,
                    onclause=InvoiceORM.invoice_id  == invoice_item_joined.c.invoice_id, 
                    isouter=False
                )
                .join(
                    journal_summary,
                    onclause=InvoiceORM.journal_id  == journal_summary.c.journal_id, 
                    isouter=False
                )
                .where(
                    *inv_filters
                )
                .order_by(InvoiceORM.invoice_dt.desc())
                .offset(offset)
                .limit(limit)
            )
            
            invoices = s.exec(invoice_joined).all()
            
        return [
            _InvoiceBrief(
                invoice_id=invoice.invoice_id,
                invoice_num=invoice.invoice_num,
                invoice_dt=invoice.invoice_dt,
                customer_id=invoice.customer_id,
                subject=invoice.subject,
                currency=invoice.currency,
                num_invoice_items=invoice.num_invoice_items,
                total_raw_amount=invoice.total_raw_amount,
                total_base_amount=invoice.total_base_amount,
            ) 
            for invoice in invoices
        ]