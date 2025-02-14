from fastapi import APIRouter
from src.app.service.entity import EntityService
from src.app.model.entity import _ContactBrief, _CustomerBrief, _SupplierBrief, Contact, Customer, Supplier

router = APIRouter(prefix="/entity", tags=["entity"])

@router.post("/contact/add")
def add_contact(contact: Contact):
    EntityService.add_contact(
        contact,
        ignore_exist=False
    )
    
@router.put("/contact/update")
def update_contact(contact: Contact):
    EntityService.update_contact(contact)
    
@router.put("/contact/upsert")
def upsert_contact(contact: Contact):
    EntityService.upsert_contact(contact)
    
@router.delete("/contact/delete/{contact_id}")
def delete_contact(contact_id: str):
    EntityService.remove_contact(contact_id=contact_id)
    
@router.get("/contact/get/{contact_id}")
def get_contact(contact_id: str) -> Contact:
    return EntityService.get_contact(contact_id)

@router.get("/contact/list")
def list_contact() -> list[_ContactBrief]:
    return EntityService.list_contact()

@router.post("/customer/add")
def add_customer(customer: Customer):
    EntityService.add_customer(customer)
    
@router.put("/customer/update")
def update_customer(customer: Customer):
    EntityService.update_customer(customer)
    
@router.put("/customer/upsert")
def upsert_customer(customer: Customer):
    EntityService.upsert_customer(customer)
    
@router.delete("/customer/delete/{cust_id}")
def delete_customer(cust_id: str):
    EntityService.remove_customer(cust_id=cust_id)
    
@router.get("/customer/get/{cust_id}")
def get_customer(cust_id: str) -> Customer:
    return EntityService.get_customer(cust_id=cust_id)

@router.get("/customer/list")
def list_customer() -> list[_CustomerBrief]:
    return EntityService.list_customer()

@router.post("/supplier/add")
def add_supplier(supplier: Supplier):
    EntityService.add_supplier(supplier)
    
@router.put("/supplier/update")
def update_supplier(supplier: Supplier):
    EntityService.update_supplier(supplier)
    
@router.put("/supplier/upsert")
def upsert_supplier(supplier: Supplier):
    EntityService.upsert_supplier(supplier)
    
@router.delete("/supplier/delete/{supplier_id}")
def delete_supplier(supplier_id: str):
    EntityService.remove_supplier(supplier_id=supplier_id)
    
@router.get("/supplier/get/{supplier_id}")
def get_supplier(supplier_id: str) -> Supplier:
    return EntityService.get_supplier(supplier_id=supplier_id)

@router.get("/supplier/list")
def list_supplier() -> list[_SupplierBrief]:
    return EntityService.list_supplier()