import logging
from typing import Dict, List
from dacite import from_dict, Config
from enum import Enum
from dataclasses import asdict
from orm import InvoiceORM
from connection import engine
from sqlmodel import Session, select
from model.invoice import Invoice

class invoiceDao:
    @classmethod
    def fromInvoice(cls, invoice: Invoice) -> InvoiceORM:
        return InvoiceORM(
            **asdict(invoice)
        )
    
    @classmethod
    def toInvoice(cls, invoice_orm: InvoiceORM) -> Invoice:
        return from_dict(
            data_class = Invoice,
            data = invoice_orm.dict(),
            config = Config(cast = [Enum])
        )
        
    @classmethod
    def add(cls, invoice: Invoice):
        invoice_orm = cls.fromInvoice(invoice)
        with Session(engine) as s:
            s.add(invoice_orm)
            s.commit()
            logging.info(f"Added {invoice_orm} to Invoice table")
    
    @classmethod
    def remove(cls, invoice_id: str):
        with Session(engine) as s:
            sql = select(InvoiceORM).where(InvoiceORM.invoice_id == invoice_id)
            p = s.exec(sql).one() # get the invoice
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Invoice table")
    
    @classmethod
    def update(cls, invoice: Invoice):
        invoice_orm = cls.fromInvoice(invoice)
        with Session(engine) as s:
            sql = select(InvoiceORM).where(InvoiceORM.invoice_id == invoice_orm.invoice_id)
            p = s.exec(sql).one() # get the invoice
            
            # update
            p.invoice_dt = invoice_orm.invoice_dt
            p.entity_id_provider = invoice_orm.entity_id_provider
            p.entity_id_payer = invoice_orm.entity_id_payer
            p.currency = invoice_orm.currency
            p.items = invoice_orm.items
            p.discount = invoice_orm.discount
            p.shipping = invoice_orm.shipping
            p.note = invoice_orm.note
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Invoice table")
    
    @classmethod
    def get(cls, invoice_id: str) -> Invoice:
        with Session(engine) as s:
            sql = select(InvoiceORM).where(InvoiceORM.invoice_id == invoice_id)
            p = s.exec(sql).one() # get the invoice
        invoice = cls.toInvoice(p)
        return invoice

    @classmethod
    def getIds(cls) -> List[str]:
        with Session(engine) as s:
            sql = select(InvoiceORM.invoice_id)
            ps = s.exec(sql).all()
        return ps


if __name__ == '__main__':
    # invoice = from_dict(
    #     data_class = Invoice,
    #     data = {
    #         'invoice_id' : 'e123',
    #         'name' : 'LTX Intelligent Service Inc.',
    #         'invoice_type' : 2,
    #         'email' : 'luntaix@ltxservice.ca',
    #         'address' : {
    #             'address1' : '33 Charles st E',
    #             'suite_no' : 1603,
    #             'city' : 'Toronto',
    #             'state' : 'Ontario',
    #             'country' : 'Canada',
    #             'postal_code' : 'M4Y0A2'
    #         },
    #         'avatar': 'LTX - logo.png'
    #     },
    #     config = Config(cast = [Enum])
    # )
    # invoiceDao.update(invoice)
    
    # print(invoiceDao.getNames())
    print(invoiceDao.get('e-41ac6'))