import logging

from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.entity import contactDao, customerDao
from src.app.model.entity import Contact, Customer

class EntityService:
    
    @classmethod
    def add_contact(cls, contact: Contact, ignore_exist: bool = False):
        try:
            contactDao.add(contact)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise AlreadyExistError(e)
            
    @classmethod
    def update_contact(cls, contact: Contact, ignore_nonexist: bool = False):
        try:
            contactDao.update(contact)
        except NotExistError as e:
            if not ignore_nonexist:
                raise NotExistError(e)
            
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
                raise NotExistError(e)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(e)
        
    @classmethod
    def get_contact(cls, contact_id: str) -> Contact:
        contact = contactDao.get(contact_id)
        return contact
    
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
                raise AlreadyExistError(e)
        except FKNotExistError as e:
            raise FKNotExistError(e)
            
    @classmethod
    def remove_customer(cls, cust_id: str, ignore_nonexist: bool = False):
        try:
            customerDao.remove(cust_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise NotExistError(e)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(e)
            
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
                raise NotExistError(e)
            
    @classmethod
    def upsert_customer(cls, customer: Customer):
        try:
            cls.add_customer(customer)
        except AlreadyExistError:
            cls.update_customer(customer)
        except FKNotExistError as e:
            raise FKNotExistError(e) # contact does not exist
            
    @classmethod
    def get_customer(cls, cust_id: str) -> Customer:
        try:
            bill_contact_id, ship_contact_id = customerDao.get_bill_ship_contact_ids(
                cust_id
            )
        except NotExistError as e:
            # customer not even exist
            raise NotExistError(e)
        
        # get contacts
        bill_contact = cls.get_contact(bill_contact_id)
        if ship_contact_id:
            ship_contact = cls.get_contact(ship_contact_id)
            
        # get customer
        customer = customerDao.get(cust_id, bill_contact, ship_contact)
        return customer