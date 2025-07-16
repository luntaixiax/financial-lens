import logging
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import EntityType
from src.app.dao.orm import ContactORM, EntityORM, EntityORM, infer_integrity_error
from src.app.model.entity import _ContactBrief, _CustomerBrief, _SupplierBrief, Address, Contact, Customer, Supplier
from src.app.model.exceptions import AlreadyExistError, NotExistError, FKNoDeleteUpdateError

class contactDao:
    
    def __init__(self, session: Session):
        self.session = session
        
    def fromContact(self, contact: Contact) -> ContactORM:
        return ContactORM(
            contact_id = contact.contact_id,
            name = contact.name,
            email = contact.email,
            phone = contact.phone,
            address = contact.address.model_dump() if contact.address else None
        )
        
        
    def toContact(self, contact_orm: ContactORM) -> Contact:
        return Contact(
            contact_id = contact_orm.contact_id,
            name = contact_orm.name,
            email = str(contact_orm.email), # special type EmailType
            phone = str(contact_orm.phone), # special type PhoneType
            address = Address.model_validate(contact_orm.address)
        )
        
        
    def add(self, contact: Contact):
        contact_orm = self.fromContact(contact)
        self.session.add(contact_orm)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistError(details=str(e))
        
        
    def remove(self, contact_id: str):
        sql = select(ContactORM).where(ContactORM.contact_id == contact_id)
        try:
            p = self.session.exec(sql).one() # get the ccount
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        try:
            self.session.delete(p)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
        
    def update(self, contact: Contact):
        contact_orm = self.fromContact(contact)

        sql = select(ContactORM).where(
            ContactORM.contact_id == contact_orm.contact_id
        )
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        if not p == contact_orm:
            # update
            p.name = contact_orm.name
            p.email = contact_orm.email
            p.phone = contact_orm.phone
            p.address = contact_orm.address
            
            self.session.add(p)
            self.session.commit()
            self.session.refresh(p) # update p to instantly have new values
                

    def get(self, contact_id: str) -> Contact:
        sql = select(ContactORM).where(
            ContactORM.contact_id == contact_id
        )
        try:
            p = self.session.exec(sql).one() # get the contact
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        return self.toContact(p)
    
    def list_contact(self) -> list[_ContactBrief]:
        sql = select(ContactORM.contact_id, ContactORM.name)
        contacts = self.session.exec(sql).all()

        return [_ContactBrief(contact_id=c.contact_id, name=c.name) for c in contacts]
    

class customerDao:
    
    def __init__(self, session: Session):
        self.session = session

    def fromCustomer(self, customer: Customer) -> EntityORM:
        return EntityORM(
            entity_id=customer.cust_id,
            entity_type=EntityType.CUSTOMER,
            entity_name=customer.customer_name,
            is_business=customer.is_business,
            bill_contact_id=customer.bill_contact.contact_id,
            ship_same_as_bill=customer.ship_same_as_bill,
            ship_contact_id=customer.ship_contact.contact_id if customer.ship_contact else None,
        )
        
    def toCustomer(self, customer_orm: EntityORM, bill_contact: Contact, ship_contact: Contact | None) -> Customer:
        return Customer(
            cust_id=customer_orm.entity_id,
            customer_name=customer_orm.entity_name,
            is_business=customer_orm.is_business,
            bill_contact=bill_contact,
            ship_same_as_bill=customer_orm.ship_same_as_bill,
            ship_contact=ship_contact,
        )
        
    def add(self, customer: Customer):
        customer_orm = self.fromCustomer(customer)
        self.session.add(customer_orm)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise infer_integrity_error(e, during_creation=True)
            
    def remove(self, cust_id: str):
        sql = select(EntityORM).where(
            EntityORM.entity_id == cust_id,
            EntityORM.entity_type == EntityType.CUSTOMER
        )
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))

        try:
            self.session.delete(p)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
            
    def update(self, customer: Customer):
        customer_orm = self.fromCustomer(customer)

        sql = select(EntityORM).where(
            EntityORM.entity_id == customer_orm.entity_id,
            EntityORM.entity_type == EntityType.CUSTOMER
        )
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        if not p == customer_orm:
            p.entity_name = customer_orm.entity_name
            p.is_business = customer_orm.is_business
            p.bill_contact_id = customer_orm.bill_contact_id
            p.ship_same_as_bill = customer_orm.ship_same_as_bill
            p.ship_contact_id = customer_orm.ship_contact_id
            
            self.session.add(p)
            self.session.commit()
            self.session.refresh(p) # update p to instantly have new values
            
    def get(self, cust_id: str, bill_contact: Contact, ship_contact: Contact | None) -> Customer:
        sql = select(EntityORM).where(
            EntityORM.entity_id == cust_id,
            EntityORM.entity_type == EntityType.CUSTOMER
        )
        try:
            p = self.session.exec(sql).one() # get the customer
        except NoResultFound as e:
            raise NotExistError(details=str(e))
            
        return self.toCustomer(p, bill_contact, ship_contact)
    
    def get_bill_ship_contact_ids(self, cust_id: str) -> tuple[str, str | None]:
        # return bill_contact_id, ship_contact_id
        sql = select(EntityORM).where(
            EntityORM.entity_id == cust_id,
            EntityORM.entity_type == EntityType.CUSTOMER
        )
        try:
            p = self.session.exec(sql).one() # get the customer
        except NoResultFound as e:
            raise NotExistError(details=str(e))
    
        return p.bill_contact_id, p.ship_contact_id
    
    def list_customer(self) -> list[_CustomerBrief]:
        sql = (
            select(EntityORM.entity_id, EntityORM.entity_name, EntityORM.is_business)
            .where(EntityORM.entity_type == EntityType.CUSTOMER)
        )
        try:
            customers = self.session.exec(sql).all()
        except NoResultFound as e:
            return []

        return [
            _CustomerBrief(
                cust_id=c.entity_id, 
                customer_name=c.entity_name,
                is_business=c.is_business
            ) 
            for c in customers
        ]
    
    
class supplierDao:
    
    def __init__(self, session: Session):
        self.session = session
        
    def fromSupplier(self, supplier: Supplier) -> EntityORM:
        return EntityORM(
            entity_id=supplier.supplier_id,
            entity_type=EntityType.SUPPLIER,
            entity_name=supplier.supplier_name,
            is_business=supplier.is_business,
            bill_contact_id=supplier.bill_contact.contact_id,
            ship_same_as_bill=supplier.ship_same_as_bill,
            ship_contact_id=supplier.ship_contact.contact_id if supplier.ship_contact else None,
        )
        
    def toSupplier(self, supplier_orm: EntityORM, bill_contact: Contact, ship_contact: Contact | None) -> Supplier:
        return Supplier(
            supplier_id=supplier_orm.entity_id,
            supplier_name=supplier_orm.entity_name,
            is_business=supplier_orm.is_business,
            bill_contact=bill_contact,
            ship_same_as_bill=supplier_orm.ship_same_as_bill,
            ship_contact=ship_contact,
        )
            
    def add(self, supplier: Supplier):
        supplier_orm = self.fromSupplier(supplier)
        self.session.add(supplier_orm)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise infer_integrity_error(e, during_creation=True)
            
    def remove(self, supplier_id: str):
        sql = select(EntityORM).where(
            EntityORM.entity_id == supplier_id,
            EntityORM.entity_type == EntityType.SUPPLIER
        )
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))    
    
        try:
            self.session.delete(p)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
            
    def update(self, supplier: Supplier):
        supplier_orm = self.fromSupplier(supplier)
        sql = select(EntityORM).where(
            EntityORM.entity_id == supplier_orm.entity_id,
            EntityORM.entity_type == EntityType.SUPPLIER
        )
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        if not p == supplier_orm:
            # update
            p.entity_name = supplier_orm.entity_name
            p.is_business = supplier_orm.is_business
            p.bill_contact_id = supplier_orm.bill_contact_id
            p.ship_same_as_bill = supplier_orm.ship_same_as_bill
            p.ship_contact_id = supplier_orm.ship_contact_id
            
            self.session.add(p)
            self.session.commit()
            self.session.refresh(p) # update p to instantly have new values
            
    def get(self, supplier_id: str, bill_contact: Contact, ship_contact: Contact | None) -> Supplier:
        sql = select(EntityORM).where(
            EntityORM.entity_id == supplier_id,
            EntityORM.entity_type == EntityType.SUPPLIER
        )
        try:
            p = self.session.exec(sql).one() # get the supplier
        except NoResultFound as e:
            raise NotExistError(details=str(e))
            
        return self.toSupplier(p, bill_contact, ship_contact)
    
    def get_bill_ship_contact_ids(self, supplier_id: str) -> tuple[str, str | None]:
        # return bill_contact_id, ship_contact_id
        sql = select(EntityORM).where(
            EntityORM.entity_id == supplier_id,
            EntityORM.entity_type == EntityType.SUPPLIER
        )
        try:
            p = self.session.exec(sql).one() # get the supplier
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        return p.bill_contact_id, p.ship_contact_id
    
    def list_supplier(self) -> list[_SupplierBrief]:
        sql = (
            select(EntityORM.entity_id, EntityORM.entity_name, EntityORM.is_business)
            .where(EntityORM.entity_type == EntityType.SUPPLIER)
        )
        try:
            suppliers = self.session.exec(sql).all()
        except NoResultFound as e:
            return []

        return [
            _SupplierBrief(
                supplier_id=self.session.entity_id, 
                supplier_name=self.session.entity_name,
                is_business=self.session.is_business
            ) 
            for self.session in suppliers
        ]