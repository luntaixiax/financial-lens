from fastapi import APIRouter, Depends
from src.app.service.entity import EntityService
from src.app.model.entity import _ContactBrief, _CustomerBrief, _SupplierBrief, Contact, Customer, Supplier
from src.web.dependency.service import get_entity_service

router = APIRouter(prefix="/entity", tags=["entity"])

@router.post("/contact/add")
def add_contact(
    contact: Contact, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.add_contact(
        contact,
        ignore_exist=False
    )
    
@router.put("/contact/update")
def update_contact(
    contact: Contact, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.update_contact(contact)
    
@router.put("/contact/upsert")
def upsert_contact(
    contact: Contact, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.upsert_contact(contact)
    
@router.delete("/contact/delete/{contact_id}")
def delete_contact(
    contact_id: str, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.remove_contact(contact_id=contact_id)
    
@router.get("/contact/get/{contact_id}")
def get_contact(
    contact_id: str, 
    entity_service: EntityService = Depends(get_entity_service)
) -> Contact:
    return entity_service.get_contact(contact_id)

@router.get("/contact/list")
def list_contact(
    entity_service: EntityService = Depends(get_entity_service)
) -> list[_ContactBrief]:
    return entity_service.list_contact()

@router.post("/customer/add")
def add_customer(
    customer: Customer, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.add_customer(customer)
    
@router.put("/customer/update")
def update_customer(
    customer: Customer, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.update_customer(customer)
    
@router.put("/customer/upsert")
def upsert_customer(
    customer: Customer, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.upsert_customer(customer)
    
@router.delete("/customer/delete/{cust_id}")
def delete_customer(
    cust_id: str, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.remove_customer(cust_id=cust_id)
    
@router.get("/customer/get/{cust_id}")
def get_customer(
    cust_id: str, 
    entity_service: EntityService = Depends(get_entity_service)
) -> Customer:
    return entity_service.get_customer(cust_id=cust_id)

@router.get("/customer/list")
def list_customer(
    entity_service: EntityService = Depends(get_entity_service)
) -> list[_CustomerBrief]:
    return entity_service.list_customer()

@router.post("/supplier/add")
def add_supplier(
    supplier: Supplier, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.add_supplier(supplier)
    
@router.put("/supplier/update")
def update_supplier(
    supplier: Supplier, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.update_supplier(supplier)
    
@router.put("/supplier/upsert")
def upsert_supplier(
    supplier: Supplier, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.upsert_supplier(supplier)
    
@router.delete("/supplier/delete/{supplier_id}")
def delete_supplier(
    supplier_id: str, 
    entity_service: EntityService = Depends(get_entity_service)
):
    entity_service.remove_supplier(supplier_id=supplier_id)
    
@router.get("/supplier/get/{supplier_id}")
def get_supplier(
    supplier_id: str, 
    entity_service: EntityService = Depends(get_entity_service)
) -> Supplier:
    return entity_service.get_supplier(supplier_id=supplier_id)

@router.get("/supplier/list")
def list_supplier(
    entity_service: EntityService = Depends(get_entity_service)
) -> list[_SupplierBrief]:
    return entity_service.list_supplier()