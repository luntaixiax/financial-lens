import logging
import pytest
from unittest import mock
from src.app.model.exceptions import FKNoDeleteUpdateError, NotExistError, AlreadyExistError
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
def contact2() -> Contact:
    return Contact(
        name='luntaixia2',
        email='infodesk2@ltxservice.ca',
        phone='987654321',
        address=Address(
            address1='01 XX St E',
            suite_no=4321,
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
    
@pytest.fixture
def customer2(contact1, contact2) -> Customer:
    return Customer(
        customer_name = 'LTX Company 2',
        is_business=True,
        bill_contact=contact1,
        ship_same_as_bill=False,
        ship_contact=contact2
    )
    
@mock.patch("src.app.dao.connection.get_engine")
def test_pure_crud_contact(mock_engine, engine, contact1, contact2):
    mock_engine.return_value = engine
    
    from src.app.service.entity import EntityService
    
    # get should raise error
    with pytest.raises(NotExistError):
        EntityService.get_contact(contact1.contact_id)
    
    EntityService.add_contact(contact1)
    # test duplicate add, should be error
    with pytest.raises(AlreadyExistError):
        EntityService.add_contact(contact1)
    # test duplicate add, should be no error if ignore_exist is True
    EntityService.add_contact(contact1, ignore_exist=True)
    
    # test get contact
    _contact = EntityService.get_contact(contact1.contact_id)
    assert _contact == contact1
    
    # delete contact
    with pytest.raises(NotExistError):
        EntityService.remove_contact('random_contact_id')
    EntityService.remove_contact(contact1.contact_id)
    # should not be found:
    with pytest.raises(NotExistError):
        EntityService.get_contact(contact1.contact_id)
    
        
    # test update contact
    EntityService.add_contact(contact1)
    contact1.phone = '135792468'
    EntityService.update_contact(contact1)
    # test error on update contact not exist
    with pytest.raises(NotExistError):
        EntityService.update_contact(contact2)
    # and no error if ignore_nonexist is True
    EntityService.update_contact(contact2, ignore_nonexist=True)
    _contact = EntityService.get_contact(contact1.contact_id)
    assert _contact.phone == '135792468'
    assert _contact == contact1
    
    # test upsert contact
    EntityService.upsert_contact(contact2)
    _contact2 = EntityService.get_contact(contact2.contact_id)
    assert _contact2 == contact2
    
    # remove both contact
    EntityService.remove_contact(contact1.contact_id)
    EntityService.remove_contact(contact2.contact_id)
    with pytest.raises(NotExistError):
        EntityService.get_contact(contact1.contact_id)
        EntityService.get_contact(contact2.contact_id)
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_crud_single_customer(mock_engine, engine, customer1, contact2):
    mock_engine.return_value = engine
    
    from src.app.service.entity import EntityService
    
    # get should raise error
    with pytest.raises(NotExistError):
        EntityService.get_customer(customer1.cust_id)
        
    EntityService.add_customer(customer1)
    # test duplicate add, should be error
    with pytest.raises(AlreadyExistError):
        EntityService.add_customer(customer1)
    # test duplicate add, should be no error if ignore_exist is True
    EntityService.add_customer(customer1, ignore_exist=True)
    
    # see if contact is created
    EntityService.get_contact(customer1.bill_contact.contact_id)
        
    # update customer (change business)
    customer1.is_business = False
    EntityService.update_customer(customer1)
    # test error on update customer not exist
    with pytest.raises(NotExistError):
        customer2 = customer1.model_copy()
        customer2._set_skip_validation('cust_id', 'random_cust_id')
        EntityService.update_customer(customer2)
    _customer = EntityService.get_customer(customer1.cust_id)
    assert _customer.is_business == False
    assert _customer == customer1
    
    # update customer (change address)
    customer1.ship_same_as_bill = False
    customer1.ship_contact = contact2
    EntityService.update_customer(customer1)
    # test if contact2 has been added
    _contact2 = EntityService.get_contact(contact2.contact_id)
    assert _contact2 == contact2
    # test if customer is updated
    _customer = EntityService.get_customer(customer1.cust_id)
    assert _customer.ship_same_as_bill == False
    assert _customer.ship_contact == contact2
    assert _customer == customer1
    
    # test if can remove contact when referenced in customer (on_delete restrictive)
    with pytest.raises(FKNoDeleteUpdateError):
        EntityService.remove_contact(contact2.contact_id)
    
    # delete customer
    EntityService.remove_customer(customer1.cust_id)
    with pytest.raises(NotExistError):
        EntityService.get_customer(customer1.cust_id)
    
    # delete contacts (clean up)
    EntityService.remove_contact(customer1.bill_contact.contact_id)
    EntityService.remove_contact(customer1.ship_contact.contact_id)
    
    # test upsert
    EntityService.upsert_customer(customer1)
    _customer = EntityService.get_customer(customer1.cust_id)
    assert _customer == customer1
    # update
    customer1.is_business == False
    EntityService.upsert_customer(customer1)
    _customer = EntityService.get_customer(customer1.cust_id)
    assert _customer.is_business == False
    
    # delete (clean up)
    EntityService.remove_customer(customer1.cust_id)
    EntityService.remove_contact(customer1.bill_contact.contact_id)
    EntityService.remove_contact(customer1.ship_contact.contact_id)
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_crud_two_customer(mock_engine, engine, customer1, customer2):
    mock_engine.return_value = engine
    
    from src.app.service.entity import EntityService
    
    EntityService.add_customer(customer1)
    # customer1 and 2 share 1 of same address
    EntityService.add_customer(customer2)
    
    # test two contacts are added
    _contact1 = EntityService.get_contact(customer1.bill_contact.contact_id)
    assert _contact1 == customer1.bill_contact
    _contact2 = EntityService.get_contact(customer2.ship_contact.contact_id)
    assert _contact2 == customer2.ship_contact
    
    # test foreinkey work
    with pytest.raises(FKNoDeleteUpdateError):
        EntityService.remove_contact(_contact2.contact_id)
        
    # remove customer 2
    EntityService.remove_customer(customer2.cust_id)
    # remove ship contact
    EntityService.remove_contact(customer2.ship_contact.contact_id)
    # remove customer 1
    EntityService.remove_customer(customer1.cust_id)
    EntityService.remove_contact(customer1.bill_contact.contact_id)