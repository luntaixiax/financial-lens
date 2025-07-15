from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.entity import contactDao, customerDao, supplierDao
from src.app.model.entity import _ContactBrief, _CustomerBrief, _SupplierBrief, Address, Contact, Customer, Supplier

class EntityService:
    
    def __init__(self, contact_dao: contactDao, customer_dao: customerDao, supplier_dao: supplierDao):
        self.contact_dao = contact_dao
        self.customer_dao = customer_dao
        self.supplier_dao = supplier_dao
    
    def create_sample(self):
        # create contact
        contact = Contact(
            contact_id='cont-sample',
            name='Sample Inc.',
            email='questionme@sample.inc',
            phone='+1(234)567-8910',
            address=Address(
                address1='00 XX St E',
                address2=None,
                suite_no=1234,
                city='Toronto',
                state='Ontario',
                country='Canada',
                postal_code='XYZABC'
            )
        )
        self.add_contact(contact)
        # create customer
        customer = Customer(
            cust_id='cust-sample',
            customer_name = 'LTX Company',
            is_business=True,
            bill_contact=contact,
            ship_same_as_bill=True,
            ship_contact=None
        )
        self.add_customer(customer)
        # create supplier (same name)
        supplier = Supplier(
            supplier_id='supp-sample',
            supplier_name = 'LTX Company',
            is_business=True,
            bill_contact=contact,
            ship_same_as_bill=True,
            ship_contact=None
        )
        self.add_supplier(supplier)
        
    def clear_sample(self):
        self.remove_customer('cust-sample')
        self.remove_supplier('supp-sample')
        self.remove_contact('cont-sample')
    
    def add_contact(self, contact: Contact, ignore_exist: bool = False):
        try:
            self.contact_dao.add(contact)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise e
    def update_contact(self, contact: Contact, ignore_nonexist: bool = False):
        try:
            self.contact_dao.update(contact)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
            
    def upsert_contact(self, contact: Contact):
        try:
            self.contact_dao.add(contact)
        except AlreadyExistError:
            self.contact_dao.update(contact)
        
    def remove_contact(self, contact_id: str, ignore_nonexist: bool = False):
        try:
            self.contact_dao.remove(contact_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        except FKNoDeleteUpdateError as e:
            raise e
        
    def get_contact(self, contact_id: str) -> Contact:
        contact = self.contact_dao.get(contact_id)
        return contact
    
    def list_contact(self) -> list[_ContactBrief]:
        contacts = self.contact_dao.list_contact()
        return contacts
    
    def add_customer(self, customer: Customer, ignore_exist: bool = False):
        # add contact first
        self.upsert_contact(customer.bill_contact)
        
        if not customer.ship_same_as_bill:
            # only add ship contact if not same as bill contact
            self.upsert_contact(customer.ship_contact) # type: ignore
        
        # add customer
        try:
            self.customer_dao.add(customer)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise e
        except FKNotExistError as e:
            raise e
            
    def remove_customer(self, cust_id: str, ignore_nonexist: bool = False):
        try:
            self.customer_dao.remove(cust_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        except FKNoDeleteUpdateError as e:
            raise e
            
    def update_customer(self, customer: Customer, ignore_nonexist: bool = False):
        # if contact changed, it will create new entry in contact (if not duplicate)
        # otherwise update the contact if contact id found
        # upsert bill contact first
        self.upsert_contact(customer.bill_contact)
        
        if not customer.ship_same_as_bill:
            # upsert shipping contact
            self.upsert_contact(customer.ship_contact) # type: ignore
        
        try:
            self.customer_dao.update(customer)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
            
    def upsert_customer(self, customer: Customer):
        try:
            self.add_customer(customer)
        except AlreadyExistError:
            self.update_customer(customer)
        except FKNotExistError as e:
            raise e # contact does not exist
            
    def get_customer(self, cust_id: str) -> Customer:
        try:
            bill_contact_id, ship_contact_id = self.customer_dao.get_bill_ship_contact_ids(
                cust_id
            )
        except NotExistError as e:
            # customer not even exist
            raise e
        
        # get contacts
        bill_contact = self.get_contact(bill_contact_id)
        if ship_contact_id:
            ship_contact = self.get_contact(ship_contact_id)
            
        # get customer
        customer = self.customer_dao.get(cust_id, bill_contact, ship_contact)
        return customer
    
    def list_customer(self) -> list[_CustomerBrief]:
        customers = self.customer_dao.list_customer()
        return customers
    
    
    def add_supplier(self, supplier: Supplier, ignore_exist: bool = False):
        # add contact first
        self.upsert_contact(supplier.bill_contact)
        
        if not supplier.ship_same_as_bill:
            # only add ship contact if not same as bill contact
            self.upsert_contact(supplier.ship_contact) # type: ignore
        
        # add supplier
        try:
            self.supplier_dao.add(supplier)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise e
        except FKNotExistError as e:
            raise e
            
    def remove_supplier(self, supplier_id: str, ignore_nonexist: bool = False):
        try:
            self.supplier_dao.remove(supplier_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        except FKNoDeleteUpdateError as e:
            raise e
            
    def update_supplier(self, supplier: Supplier, ignore_nonexist: bool = False):
        # if contact changed, it will create new entry in contact (if not duplicate)
        # otherwise update the contact if contact id found
        # upsert bill contact first
        self.upsert_contact(supplier.bill_contact)
        
        if not supplier.ship_same_as_bill:
            # upsert shipping contact
            self.upsert_contact(supplier.ship_contact) # type: ignore
        
        try:
            self.supplier_dao.update(supplier)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
            
    def upsert_supplier(self, supplier: Supplier):
        try:
            self.add_supplier(supplier)
        except AlreadyExistError:
            self.update_supplier(supplier)
        except FKNotExistError as e:
            raise e # contact does not exist
            
    def get_supplier(self, supplier_id: str) -> Supplier:
        try:
            bill_contact_id, ship_contact_id = self.supplier_dao.get_bill_ship_contact_ids(
                supplier_id
            )
        except NotExistError as e:
            # supplier not even exist
            raise e
        
        # get contacts
        bill_contact = self.get_contact(bill_contact_id)
        if ship_contact_id:
            ship_contact = self.get_contact(ship_contact_id)
            
        # get supplier
        supplier = self.supplier_dao.get(supplier_id, bill_contact, ship_contact)
        return supplier
    
    def list_supplier(self) -> list[_SupplierBrief]:
        suppliers = self.supplier_dao.list_supplier()
        return suppliers