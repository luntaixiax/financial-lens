
import logging
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.dao.orm import ContactORM, CustomerORM, SupplierORM
from src.app.model.entity import Contact, Customer, Supplier
from src.app.model.exceptions import AlreadyExistError, NotExistError
from src.app.dao.connection import get_engine

class contactDao:
    @classmethod
    def fromContact(cls, contact: Contact) -> ContactORM:
        return ContactORM.model_validate(
            contact.model_dump_json()
        )
        
        
    @classmethod
    def toContact(cls, contact_orm: ContactORM) -> Contact:
        return Contact.model_validate(
            contact_orm.model_dump_json()
        )
        
        
    @classmethod
    def add(cls, contact: Contact):
        contact_orm = cls.fromContact(contact)
        with Session(get_engine()) as s:
            s.add(contact_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(f"Contact already exist: {contact}")
            else:
                logging.info(f"Added {contact_orm} to Contact table")
        
        
    @classmethod
    def remove(cls, contact_id: str):
        with Session(get_engine()) as s:
            sql = select(ContactORM).where(ContactORM.contact_id == contact_id)
            try:
                p = s.exec(sql).one() # get the ccount
            except NoResultFound as e:
                raise NotExistError(f"Contact not found: {contact_id}")
            
            s.delete(p)
            s.commit()
            logging.info(f"Removed {p} from Contact table")
        
        
    @classmethod
    def update(cls, contact: Contact):
        contact_orm = cls.fromContact(contact)
        with Session(get_engine()) as s:
            sql = select(ContactORM).where(
                ContactORM.contact_id == contact_orm.contact_id
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Contact not found: {contact.contact_id}")
            
            
            # update
            p.name = contact_orm.name
            p.email = contact_orm.email
            p.phone = contact_orm.phone
            p.address = contact_orm.address
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
            logging.info(f"Updated to {p} from Contact table")
        
        
    @classmethod
    def get(cls, contact_id: str) -> Contact:
        with Session(get_engine()) as s:
            sql = select(ContactORM).where(
                ContactORM.contact_id == contact_id
            )
            try:
                p = s.exec(sql).one() # get the contact
            except NoResultFound as e:
                raise NotExistError(f"Contact not found: {contact_id}")
        return cls.toAcct(p)
    

class customerDao:
    @classmethod
    def fromCustomer(cls, customer: Customer) -> CustomerORM:
        return CustomerORM(
            cust_id=customer.cust_id,
            customer_name=customer.customer_name,
            is_business=customer.is_business,
            bill_contact_id=customer.bill_contact.contact_id,
            ship_same_as_bill=customer.ship_same_as_bill,
            ship_contact_id=customer.ship_contact.contact_id,
        )
        
    @classmethod
    def toCustomer(cls, customer_orm: CustomerORM) -> Customer:
        return Customer(
            cust_id=customer_orm.cust_id,
            customer_name=customer_orm.customer_name,
            is_business=customer_orm.is_business,
            bill_contact=contactDao.get(customer_orm.bill_contact_id),
            ship_same_as_bill=customer_orm.ship_same_as_bill,
            ship_contact=contactDao.get(customer_orm.ship_contact_id),
        )
        
    @classmethod
    def add(cls, customer: Customer):
        customer_orm = cls.fromCustomer(customer)
        with Session(get_engine()) as s:
            s.add(customer_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(f"Customer already exist: {customer}")
            else:
                logging.info(f"Added {customer_orm} to Customer table")
            
    @classmethod
    def remove(cls, cust_id: str):
        with Session(get_engine()) as s:
            sql = select(CustomerORM).where(CustomerORM.cust_id == cust_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Customer not found: {cust_id}")
        
            s.delete(p)
            s.commit()
            logging.info(f"Removed {p} from Customer table")
            
    @classmethod
    def update(cls, customer: Customer):
        customer_orm = cls.fromCustomer(customer)
        with Session(get_engine()) as s:
            sql = select(CustomerORM).where(
                CustomerORM.cust_id == customer_orm.cust_id
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Customer not found: {customer.cust_id}")
            
            # update
            p.customer_name = customer_orm.customer_name
            p.is_business = customer_orm.is_business
            p.bill_contact_id = customer_orm.bill_contact_id
            p.ship_same_as_bill = customer_orm.ship_same_as_bill
            p.ship_contact_id = customer_orm.ship_contact_id
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
            logging.info(f"Updated to {p} from Customer table")
            
    @classmethod
    def get(cls, cust_id: str) -> Customer:
        with Session(get_engine()) as s:
            sql = select(CustomerORM).where(
                CustomerORM.cust_id == cust_id
            )
            try:
                p = s.exec(sql).one() # get the customer
            except NoResultFound as e:
                raise NotExistError(f"Customer not found: {cust_id}")
            
        return cls.toCustomer(p)
    
    
class supplierDao:
    @classmethod
    def fromSupplier(cls, supplier: Supplier) -> SupplierORM:
        return SupplierORM(
            supplier_id=supplier.supplier_id,
            supplier_name=supplier.supplier_name,
            is_business=supplier.is_business,
            bill_contact_id=supplier.bill_contact.contact_id,
            ship_same_as_bill=supplier.ship_same_as_bill,
            ship_contact_id=supplier.ship_contact.contact_id,
        )
        
    @classmethod
    def toSupplier(cls, supplier_orm: SupplierORM) -> Supplier:
        return Supplier(
            supplier_id=supplier_orm.supplier_id,
            supplier_name=supplier_orm.supplier_name,
            is_business=supplier_orm.is_business,
            bill_contact=contactDao.get(supplier_orm.bill_contact_id),
            ship_same_as_bill=supplier_orm.ship_same_as_bill,
            ship_contact=contactDao.get(supplier_orm.ship_contact_id),
        )
        
    @classmethod
    def add(cls, supplier: Supplier):
        supplier_orm = cls.fromSupplier(supplier)
        with Session(get_engine()) as s:
            s.add(supplier_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(f"Supplier already exist: {supplier}")
            else:
                logging.info(f"Added {supplier_orm} to Supplier table")
            
    @classmethod
    def remove(cls, supplier_id: str):
        with Session(get_engine()) as s:
            sql = select(SupplierORM).where(SupplierORM.supplier_id == supplier_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Supplier not found: {supplier_id}")    
        
        
            s.delete(p)
            s.commit()
            logging.info(f"Removed {p} from Supplier table")
            
    @classmethod
    def update(cls, supplier: Supplier):
        supplier_orm = cls.fromSupplier(supplier)
        with Session(get_engine()) as s:
            sql = select(SupplierORM).where(
                SupplierORM.supplier_id == supplier_orm.supplier_id
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Supplier not found: {supplier.supplier_id}")
            
            # update
            p.supplier_name = supplier_orm.supplier_name
            p.is_business = supplier_orm.is_business
            p.bill_contact_id = supplier_orm.bill_contact_id
            p.ship_same_as_bill = supplier_orm.ship_same_as_bill
            p.ship_contact_id = supplier_orm.ship_contact_id
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
            logging.info(f"Updated to {p} from Supplier table")
            
    @classmethod
    def get(cls, supplier_id: str) -> Supplier:
        with Session(get_engine()) as s:
            sql = select(SupplierORM).where(
                SupplierORM.supplier_id == supplier_id
            )
            try:
                p = s.exec(sql).one() # get the supplier
            except NoResultFound as e:
                raise NotExistError(f"Supplier not found: {supplier_id}")    
            
        return cls.toSupplier(p)