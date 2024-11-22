
import logging
from sqlmodel import Session, select, delete
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.invoice import InvoiceItem, Item, Invoice
from src.app.dao.orm import InvoiceItemORM, InvoiceORM, ItemORM, infer_integrity_error
from src.app.dao.connection import get_engine
from src.app.model.exceptions import AlreadyExistError, NotExistError


class itemDao:
    @classmethod
    def fromItem(cls, item: Item) -> ItemORM:
        return ItemORM.model_validate(
            item.model_dump_json()
        )
        
    @classmethod
    def toItem(cls, item_orm: ItemORM) -> Item:
        return Item.model_validate(
            item_orm.model_dump_json()
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
                raise AlreadyExistError(details=e)
            else:
                logging.info(f"Added {item_orm} to Item table")
        
        
    @classmethod
    def remove(cls, item_id: str):
        with Session(get_engine()) as s:
            sql = select(ItemORM).where(ItemORM.item_id == item_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=e)
            
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
                raise NotExistError(details=e)
            
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
                raise NotExistError(details=e)
            
        return cls.toItem(p)


class invoiceDao:
    @classmethod
    def fromInvoiceItem(cls, invoice_id: str, invoice_item: InvoiceItem) -> InvoiceItemORM:
        return InvoiceItemORM(
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
            logging.info(f"Added {invoice_orm} to invoice table")
            
            # add invoice items
            for invoice_item in invoice.invoice_items:
                invoice_item_orm = cls.fromInvoiceItem(
                    invoice_id=Invoice.invoice_id,
                    invoice_item=invoice_item
                )
                s.add(invoice_item_orm)
                logging.info(f"Added {invoice_item_orm} to invoice Item table")
            
            # commit both
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
    def update(cls, invoice: Invoice):
        # delete the given invoice and create new one
        cls.remove(invoice_id = invoice.invoice_id)
        # add the new one
        cls.add(invoice)
        logging.info(f"updated {invoice} by removing existing one and added new one")
            
    @classmethod
    def get(cls, invoice_id: str) -> Invoice:
        with Session(get_engine()) as s:
            # get invoice items
            sql = select(InvoiceItemORM).where(
                InvoiceItemORM.invoice_id == invoice_id
            )
            try:
                invoice_item_orms = s.exec(sql).all()
            except NoResultFound as e:
                raise NotExistError(details=e)

            # get invoice
            sql = select(InvoiceORM).where(
                InvoiceORM.invoice_id == invoice_id
            )
            try:
                invoice_orm = s.exec(sql).one() # get the invoice
            except NoResultFound as e:
                raise NotExistError(details=e)
            
            invoice = cls.toInvoice(
                invoice_orm=invoice_orm,
                invoice_item_orms=invoice_item_orms
            )
        return invoice