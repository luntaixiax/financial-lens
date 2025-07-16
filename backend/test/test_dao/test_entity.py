
from unittest import mock
import pytest
from src.app.model.exceptions import NotExistError, AlreadyExistError, FKNotExistError

def test_contact(test_contact_dao, contact1):
    
    # assert contact not found, and have correct error type
    with pytest.raises(NotExistError):
        test_contact_dao.get(contact_id=contact1.contact_id)
    
    # add contact
    test_contact_dao.add(contact = contact1)
    _contact = test_contact_dao.get(contact_id=contact1.contact_id)
    assert _contact == contact1
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_contact_dao.add(contact = contact1)
    
    # update contact
    contact1.name = 'mynewname'
    test_contact_dao.update(contact1)
    _contact = test_contact_dao.get(contact_id=contact1.contact_id)
    assert _contact.name == 'mynewname'
    assert _contact == contact1
    
    # delete contact
    test_contact_dao.remove(contact1.contact_id)
    with pytest.raises(NotExistError):
        test_contact_dao.get(contact_id=contact1.contact_id)
    
def test_customer(test_customer_dao, test_contact_dao, customer1):

    # assert customer not found, and have correct error type
    with pytest.raises(NotExistError):
        test_customer_dao.get(
            cust_id=customer1.cust_id,
            bill_contact=customer1.bill_contact,
            ship_contact=customer1.ship_contact,
        )
    
    # add customer
    # should raise error because contact does not exist:
    with pytest.raises(FKNotExistError):
        test_customer_dao.add(customer = customer1)
        
    # add contact as well
    test_contact_dao.add(contact = customer1.bill_contact)
    # add customer
    test_customer_dao.add(customer = customer1)
    
    _customer = test_customer_dao.get(
        cust_id=customer1.cust_id,
        bill_contact=customer1.bill_contact,
        ship_contact=customer1.ship_contact,
    )
    assert _customer == customer1
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_customer_dao.add(customer = customer1)
    
    # update contact
    customer1.customer_name = 'mynewname'
    test_customer_dao.update(customer1)
    _customer = test_customer_dao.get(
        cust_id=customer1.cust_id,
        bill_contact=customer1.bill_contact,
        ship_contact=customer1.ship_contact,
    )
    assert _customer.customer_name == 'mynewname'
    assert _customer == customer1
    
    # delete customer
    test_customer_dao.remove(customer1.cust_id)
    with pytest.raises(NotExistError):
        test_customer_dao.get(
            cust_id=customer1.cust_id,
            bill_contact=customer1.bill_contact,
            ship_contact=customer1.ship_contact,
        )
    
    # delete contact
    test_contact_dao.remove(customer1.bill_contact.contact_id)