from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import Response

from src.app.model.exceptions import AlreadyExistError
from src.app.service.entity import EntityService
from src.app.model.entity import _Contact, _ContactBrief, _Customer, _CustomerBrief, Contact, Customer

router = APIRouter(prefix="/entity", tags=["entity"])

@router.post("/contact/add")
def add_contact(contact: _Contact):
    contact: Contact = EntityService.to_contact(contact)
    EntityService.add_contact(
        contact,
        ignore_exist=False
    )
    
@router.put("/contact/update/{contact_id}")
def put_contact(contact_id: str, contact: _Contact):
    contact: Contact = EntityService.to_contact(contact, contact_id=contact_id)
    EntityService.update_contact(
        contact,
        ignore_nonexist=False
    )
    
@router.delete("/contact/delete/{contact_id}")
def delete_contact(contact_id: str):
    EntityService.remove_contact(contact_id=contact_id)
    
@router.get("/contact/get/{contact_id}")
def get_contact(contact_id: str) -> _Contact:
    contact: Contact = EntityService.get_contact(contact_id)
    return EntityService.from_contact(contact)

@router.get("/contact/list")
def list_contact() -> list[_ContactBrief]:
    return EntityService.list_contact()

@router.post("/customer/add")
def add_customer(customer: _Customer):
    customer: Customer = EntityService.to_customer(customer)
    EntityService.add_customer(customer)
    
@router.put("/customer/update/{cust_id}")
def put_contact(cust_id: str, customer: _Customer):
    customer: Customer = EntityService.to_customer(customer, cust_id=cust_id)
    EntityService.update_customer(customer)
    
@router.delete("/customer/delete/{cust_id}")
def delete_customer(cust_id: str):
    EntityService.remove_customer(cust_id=cust_id)
    
@router.get("/customer/get/{cust_id}")
def get_customer(cust_id: str) -> _Customer:
    customer: Customer = EntityService.get_customer(cust_id=cust_id)
    return EntityService.from_customer(customer)

@router.get("/customer/list")
def list_customer() -> list[_CustomerBrief]:
    return EntityService.list_customer()