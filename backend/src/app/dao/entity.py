
import logging
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import EntityType
from src.app.dao.orm import ContactORM, EntityORM, EntityORM, infer_integrity_error
from src.app.model.entity import _ContactBrief, _CustomerBrief, _SupplierBrief, Address, Contact, Customer, Supplier
from src.app.model.exceptions import AlreadyExistError, NotExistError, FKNoDeleteUpdateError
from src.app.dao.connection import get_engine

class contactDao:
    @classmethod
    def fromContact(cls, contact: Contact) -> ContactORM:
        return ContactORM(
            contact_id = contact.contact_id,
            name = contact.name,
            email = contact.email,
            phone = contact.phone,
            address = contact.address.model_dump()
        )
        
        
    @classmethod
    def toContact(cls, contact_orm: ContactORM) -> Contact:
        return Contact(
            contact_id = contact_orm.contact_id,
            name = contact_orm.name,
            email = str(contact_orm.email), # special type EmailType
            phone = str(contact_orm.phone), # special type PhoneType
            address = Address.model_validate(contact_orm.address)
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
                raise AlreadyExistError(details=str(e))
            else:
                logging.info(f"Added {contact_orm} to Contact table")
        
        
    @classmethod
    def remove(cls, contact_id: str):
        with Session(get_engine()) as s:
            sql = select(ContactORM).where(ContactORM.contact_id == contact_id)
            try:
                p = s.exec(sql).one() # get the ccount
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(details=str(e))
            
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
                raise NotExistError(details=str(e))
            
            if not p == contact_orm:
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
                raise NotExistError(details=str(e))
        return cls.toContact(p)
    
    @classmethod
    def list_contact(cls) -> list[_ContactBrief]:
        with Session(get_engine()) as s:
            sql = select(ContactORM.contact_id, ContactORM.name)
            contacts = s.exec(sql).all()

        return [_ContactBrief(contact_id=c.contact_id, name=c.name) for c in contacts]
    

class customerDao:
    @classmethod
    def fromCustomer(cls, customer: Customer) -> EntityORM:
        return EntityORM(
            entity_id=customer.cust_id,
            entity_type=EntityType.CUSTOMER,
            entity_name=customer.customer_name,
            is_business=customer.is_business,
            bill_contact_id=customer.bill_contact.contact_id,
            ship_same_as_bill=customer.ship_same_as_bill,
            ship_contact_id=customer.ship_contact.contact_id,
        )
        
    @classmethod
    def toCustomer(cls, customer_orm: EntityORM, bill_contact: Contact, ship_contact: Contact | None) -> Customer:
        return Customer(
            cust_id=customer_orm.entity_id,
            customer_name=customer_orm.entity_name,
            is_business=customer_orm.is_business,
            bill_contact=bill_contact,
            ship_same_as_bill=customer_orm.ship_same_as_bill,
            ship_contact=ship_contact,
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
                raise infer_integrity_error(e, during_creation=True)
            else:
                logging.info(f"Added {customer_orm} to Customer table")
            
    @classmethod
    def remove(cls, cust_id: str):
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == cust_id,
                EntityORM.entity_type == EntityType.CUSTOMER
            )
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
            logging.info(f"Removed {p} from Customer table")
            
    @classmethod
    def update(cls, customer: Customer):
        customer_orm = cls.fromCustomer(customer)
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == customer_orm.entity_id,
                EntityORM.entity_type == EntityType.CUSTOMER
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            if not p == customer_orm:
                p.entity_name = customer_orm.entity_name
                p.is_business = customer_orm.is_business
                p.bill_contact_id = customer_orm.bill_contact_id
                p.ship_same_as_bill = customer_orm.ship_same_as_bill
                p.ship_contact_id = customer_orm.ship_contact_id
                
                s.add(p)
                s.commit()
                s.refresh(p) # update p to instantly have new values
                
                logging.info(f"Updated to {p} from Customer table")
            
    @classmethod
    def get(cls, cust_id: str, bill_contact: Contact, ship_contact: Contact | None) -> Customer:
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == cust_id,
                EntityORM.entity_type == EntityType.CUSTOMER
            )
            try:
                p = s.exec(sql).one() # get the customer
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return cls.toCustomer(p, bill_contact, ship_contact)
    
    @classmethod
    def get_bill_ship_contact_ids(cls, cust_id: str) -> tuple[str, str | None]:
        # return bill_contact_id, ship_contact_id
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == cust_id,
                EntityORM.entity_type == EntityType.CUSTOMER
            )
            try:
                p = s.exec(sql).one() # get the customer
            except NoResultFound as e:
                raise NotExistError(details=str(e))
        
        return p.bill_contact_id, p.ship_contact_id
    
    @classmethod
    def list_customer(cls) -> list[_CustomerBrief]:
        with Session(get_engine()) as s:
            sql = (
                select(EntityORM.entity_id, EntityORM.entity_name, EntityORM.is_business)
                .where(EntityORM.entity_type == EntityType.CUSTOMER)
            )
            customers = s.exec(sql).all()

        return [
            _CustomerBrief(
                cust_id=c.entity_id, 
                customer_name=c.entity_name,
                is_business=c.is_business
            ) 
            for c in customers
        ]
    
    
class supplierDao:
    @classmethod
    def fromSupplier(cls, supplier: Supplier) -> EntityORM:
        return EntityORM(
            entity_id=supplier.supplier_id,
            entity_type=EntityType.SUPPLIER,
            entity_name=supplier.supplier_name,
            is_business=supplier.is_business,
            bill_contact_id=supplier.bill_contact.contact_id,
            ship_same_as_bill=supplier.ship_same_as_bill,
            ship_contact_id=supplier.ship_contact.contact_id,
        )
        
    @classmethod
    def toSupplier(cls, supplier_orm: EntityORM, bill_contact: Contact, ship_contact: Contact | None) -> Supplier:
        return Supplier(
            supplier_id=supplier_orm.entity_id,
            supplier_name=supplier_orm.entity_name,
            is_business=supplier_orm.is_business,
            bill_contact=bill_contact,
            ship_same_as_bill=supplier_orm.ship_same_as_bill,
            ship_contact=ship_contact,
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
                raise infer_integrity_error(e, during_creation=True)
            else:
                logging.info(f"Added {supplier_orm} to Supplier table")
            
    @classmethod
    def remove(cls, supplier_id: str):
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == supplier_id,
                EntityORM.entity_type == EntityType.SUPPLIER
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))    
        
        
            s.delete(p)
            s.commit()
            logging.info(f"Removed {p} from Supplier table")
            
    @classmethod
    def update(cls, supplier: Supplier):
        supplier_orm = cls.fromSupplier(supplier)
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == supplier_orm.entity_id,
                EntityORM.entity_type == EntityType.SUPPLIER
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            if not p == supplier_orm:
                # update
                p.entity_name = supplier_orm.entity_name
                p.is_business = supplier_orm.is_business
                p.bill_contact_id = supplier_orm.bill_contact_id
                p.ship_same_as_bill = supplier_orm.ship_same_as_bill
                p.ship_contact_id = supplier_orm.ship_contact_id
                
                s.add(p)
                s.commit()
                s.refresh(p) # update p to instantly have new values
                
                logging.info(f"Updated to {p} from Supplier table")
            
    @classmethod
    def get(cls, supplier_id: str, bill_contact: Contact, ship_contact: Contact | None) -> Supplier:
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == supplier_id,
                EntityORM.entity_type == EntityType.SUPPLIER
            )
            try:
                p = s.exec(sql).one() # get the supplier
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return cls.toSupplier(p, bill_contact, ship_contact)
    
    @classmethod
    def get_bill_ship_contact_ids(cls, supplier_id: str) -> tuple[str, str | None]:
        # return bill_contact_id, ship_contact_id
        with Session(get_engine()) as s:
            sql = select(EntityORM).where(
                EntityORM.entity_id == supplier_id,
                EntityORM.entity_type == EntityType.SUPPLIER
            )
            try:
                p = s.exec(sql).one() # get the supplier
            except NoResultFound as e:
                raise NotExistError(details=str(e))
        
        return p.bill_contact_id, p.ship_contact_id
    
    @classmethod
    def list_supplier(cls) -> list[_SupplierBrief]:
        with Session(get_engine()) as s:
            sql = (
                select(EntityORM.entity_id, EntityORM.entity_name, EntityORM.is_business)
                .where(EntityORM.entity_type == EntityType.SUPPLIER)
            )
            suppliers = s.exec(sql).all()

        return [
            _SupplierBrief(
                supplier_id=s.entity_id, 
                supplier_name=s.entity_name,
                is_business=s.is_business
            ) 
            for s in suppliers
        ]