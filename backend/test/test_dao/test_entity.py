
from unittest import mock
import pytest
from src.app.model.exceptions import NotExistError, AlreadyExistError, FKNotExistError
from src.app.model.entity import Address, Contact, Customer

@pytest.fixture
def contact1() -> Contact:
    return Contact(
        name='luntaixia',
        email='infodesk@ltxservice.ca',
        phone='123456789',
        address=Address(
            address1='00 XX St E',
            suite_no=1234,
            city='Toronto',
            state='ON',
            country='Canada',
            postal_code='XYZABC'
        )
    )
    
@pytest.fixture
def customer1(contact1) -> Customer:
    return Customer(
        customer_name = 'LTX Company',
        is_business=True,
        bill_contact=contact1,
        ship_same_as_bill=True
    )

@mock.patch("src.app.dao.connection.get_engine")
def test_contact(mock_engine, engine, contact1):
    mock_engine.return_value = engine
    
    from src.app.dao.entity import contactDao
    
    # assert contact not found, and have correct error type
    with pytest.raises(NotExistError):
        contactDao.get(contact_id=contact1.contact_id)
    
    # add contact
    contactDao.add(contact = contact1)
    _contact = contactDao.get(contact_id=contact1.contact_id)
    assert _contact == contact1
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        contactDao.add(contact = contact1)
    
    # update contact
    contact1.name = 'mynewname'
    contactDao.update(contact1)
    _contact = contactDao.get(contact_id=contact1.contact_id)
    assert _contact.name == 'mynewname'
    assert _contact == contact1
    
    # delete contact
    contactDao.remove(contact1.contact_id)
    with pytest.raises(NotExistError):
        contactDao.get(contact_id=contact1.contact_id)
    
@mock.patch("src.app.dao.connection.get_engine")
def test_customer(mock_engine, engine, customer1):
    mock_engine.return_value = engine
    
    from src.app.dao.entity import customerDao, contactDao

    # assert customer not found, and have correct error type
    with pytest.raises(NotExistError):
        customerDao.get(
            cust_id=customer1.cust_id,
            bill_contact=customer1.bill_contact,
            ship_contact=customer1.ship_contact,
        )
    
    # add customer
    # should raise error because contact does not exist:
    with pytest.raises(FKNotExistError):
        customerDao.add(customer = customer1)
        
    # add contact as well
    contactDao.add(contact = customer1.bill_contact)
    # add customer
    customerDao.add(customer = customer1)
    
    _customer = customerDao.get(
        cust_id=customer1.cust_id,
        bill_contact=customer1.bill_contact,
        ship_contact=customer1.ship_contact,
    )
    assert _customer == customer1
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        customerDao.add(customer = customer1)
    
    # update contact
    customer1.customer_name = 'mynewname'
    customerDao.update(customer1)
    _customer = customerDao.get(
        cust_id=customer1.cust_id,
        bill_contact=customer1.bill_contact,
        ship_contact=customer1.ship_contact,
    )
    assert _customer.customer_name == 'mynewname'
    assert _customer == customer1
    
    # delete customer
    customerDao.remove(customer1.cust_id)
    with pytest.raises(NotExistError):
        customerDao.get(
            cust_id=customer1.cust_id,
            bill_contact=customer1.bill_contact,
            ship_contact=customer1.ship_contact,
        )
    
    # delete contact
    contactDao.remove(customer1.bill_contact.contact_id)