import logging

from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.entity import contactDao, customerDao
from src.app.model.entity import _Contact, _ContactBrief, _Customer, _CustomerBrief, Contact, Customer

class EntityService:
    
    @classmethod
    def add_contact(cls, contact: Contact, ignore_exist: bool = False):
        try:
            contactDao.add(contact)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise e
            
    @classmethod
    def update_contact(cls, contact: Contact, ignore_nonexist: bool = False):
        try:
            contactDao.update(contact)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
            
    @classmethod
    def upsert_contact(cls, contact: Contact):
        try:
            contactDao.add(contact)
        except AlreadyExistError:
            contactDao.update(contact)
        
    @classmethod
    def remove_contact(cls, contact_id: str, ignore_nonexist: bool = False):
        try:
            contactDao.remove(contact_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        except FKNoDeleteUpdateError as e:
            raise e
        
    @classmethod
    def get_contact(cls, contact_id: str) -> Contact:
        contact = contactDao.get(contact_id)
        return contact
    
    @classmethod
    def list_contact(cls) -> list[_ContactBrief]:
        contacts = contactDao.list_contact()
        return contacts
    
    @classmethod
    def to_contact(cls, contact: _Contact, contact_id: str | None = None) -> Contact:
        c = contact.model_dump()
        if contact_id:
            c.update(dict(contact_id=contact_id))
        return Contact.model_validate(c)
    
    @classmethod
    def from_contact(cls, contact: Contact) -> _Contact:
        c = contact.model_dump()
        del c['contact_id']
        return _Contact.model_validate(c)
    
    @classmethod
    def to_customer(cls, customer: _Customer, cust_id: str | None = None) -> Customer:
            
        c = dict(
            customer_name=customer.customer_name,
            is_business=customer.is_business,
            bill_contact=cls.get_contact(contact_id=customer.bill_contact_id),
            ship_same_as_bill=customer.ship_same_as_bill,
        )
        if customer.ship_contact_id:
            c.update(
                dict(ship_contact=cls.get_contact(
                    contact_id=customer.ship_contact_id
                    )
                )
            )
        if cust_id:
            c.update(dict(cust_id=cust_id))
        
        c = Customer.model_validate(c)
        return c
    
    @classmethod
    def from_customer(cls, customer: Customer) -> _Customer:
        if customer.ship_contact:
            ship_contact_id = customer.ship_contact.contact_id
        else:
            ship_contact_id = None
        return _Customer(
            customer_name=customer.customer_name,
            is_business=customer.is_business,
            bill_contact_id=customer.bill_contact.contact_id,
            ship_same_as_bill=customer.ship_same_as_bill,
            ship_contact_id=ship_contact_id
        )
    
    
    @classmethod
    def add_customer(cls, customer: Customer, ignore_exist: bool = False):
        # add contact first
        cls.upsert_contact(customer.bill_contact)
        
        if not customer.ship_same_as_bill:
            # only add ship contact if not same as bill contact
            cls.upsert_contact(customer.ship_contact)
        
        # add customer
        try:
            customerDao.add(customer)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise e
        except FKNotExistError as e:
            raise e
            
    @classmethod
    def remove_customer(cls, cust_id: str, ignore_nonexist: bool = False):
        try:
            customerDao.remove(cust_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        except FKNoDeleteUpdateError as e:
            raise e
            
    @classmethod
    def update_customer(cls, customer: Customer, ignore_nonexist: bool = False):
        # if contact changed, it will create new entry in contact (if not duplicate)
        # otherwise update the contact if contact id found
        # upsert bill contact first
        cls.upsert_contact(customer.bill_contact)
        
        if not customer.ship_same_as_bill:
            # upsert shipping contact
            cls.upsert_contact(customer.ship_contact)
        
        try:
            customerDao.update(customer)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
            
    @classmethod
    def upsert_customer(cls, customer: Customer):
        try:
            cls.add_customer(customer)
        except AlreadyExistError:
            cls.update_customer(customer)
        except FKNotExistError as e:
            raise e # contact does not exist
            
    @classmethod
    def get_customer(cls, cust_id: str) -> Customer:
        try:
            bill_contact_id, ship_contact_id = customerDao.get_bill_ship_contact_ids(
                cust_id
            )
        except NotExistError as e:
            # customer not even exist
            raise e
        
        # get contacts
        bill_contact = cls.get_contact(bill_contact_id)
        if ship_contact_id:
            ship_contact = cls.get_contact(ship_contact_id)
            
        # get customer
        customer = customerDao.get(cust_id, bill_contact, ship_contact)
        return customer
    
    @classmethod
    def list_customer(cls) -> list[_CustomerBrief]:
        customers = customerDao.list_customer()
        return customers