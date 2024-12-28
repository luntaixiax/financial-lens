import logging

from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.entity import contactDao, customerDao, supplierDao
from src.app.model.entity import _ContactBrief, _CustomerBrief, _SupplierBrief, Address, Contact, Customer, Supplier

class EntityService:
    
    @classmethod
    def create_sample(cls):
        # create contact
        contact = Contact(
            contact_id='cont-sample',
            name='Sample Inc.',
            email='questionme@sample.inc',
            phone='+1(234)567-8910',
            address=Address(
                address1='00 XX St E',
                suite_no=1234,
                city='Toronto',
                state='ON',
                country='Canada',
                postal_code='XYZABC'
            )
        )
        cls.add_contact(contact)
        # create customer
        customer = Customer(
            cust_id='cust-sample',
            customer_name = 'LTX Company',
            is_business=True,
            bill_contact=contact,
            ship_same_as_bill=True
        )
        cls.add_customer(customer)
        # create supplier (same name)
        supplier = Supplier(
            supplier_id='supp-sample',
            supplier_name = 'LTX Company',
            is_business=True,
            bill_contact=contact,
            ship_same_as_bill=True
        )
        cls.add_supplier(supplier)
        
    @classmethod
    def clear_sample(cls):
        cls.remove_customer('cust-sample')
        cls.remove_supplier('supp-sample')
        cls.remove_contact('cont-sample')
    
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
    
    
    @classmethod
    def add_supplier(cls, supplier: Supplier, ignore_exist: bool = False):
        # add contact first
        cls.upsert_contact(supplier.bill_contact)
        
        if not supplier.ship_same_as_bill:
            # only add ship contact if not same as bill contact
            cls.upsert_contact(supplier.ship_contact)
        
        # add supplier
        try:
            supplierDao.add(supplier)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise e
        except FKNotExistError as e:
            raise e
            
    @classmethod
    def remove_supplier(cls, cust_id: str, ignore_nonexist: bool = False):
        try:
            supplierDao.remove(cust_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        except FKNoDeleteUpdateError as e:
            raise e
            
    @classmethod
    def update_supplier(cls, supplier: Supplier, ignore_nonexist: bool = False):
        # if contact changed, it will create new entry in contact (if not duplicate)
        # otherwise update the contact if contact id found
        # upsert bill contact first
        cls.upsert_contact(supplier.bill_contact)
        
        if not supplier.ship_same_as_bill:
            # upsert shipping contact
            cls.upsert_contact(supplier.ship_contact)
        
        try:
            supplierDao.update(supplier)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
            
    @classmethod
    def upsert_supplier(cls, supplier: Supplier):
        try:
            cls.add_supplier(supplier)
        except AlreadyExistError:
            cls.update_supplier(supplier)
        except FKNotExistError as e:
            raise e # contact does not exist
            
    @classmethod
    def get_supplier(cls, cust_id: str) -> Supplier:
        try:
            bill_contact_id, ship_contact_id = supplierDao.get_bill_ship_contact_ids(
                cust_id
            )
        except NotExistError as e:
            # supplier not even exist
            raise e
        
        # get contacts
        bill_contact = cls.get_contact(bill_contact_id)
        if ship_contact_id:
            ship_contact = cls.get_contact(ship_contact_id)
            
        # get supplier
        supplier = supplierDao.get(cust_id, bill_contact, ship_contact)
        return supplier
    
    @classmethod
    def list_supplier(cls) -> list[_SupplierBrief]:
        suppliers = supplierDao.list_supplier()
        return suppliers