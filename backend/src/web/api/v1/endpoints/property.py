from datetime import date
from typing import Tuple
from fastapi import APIRouter
from src.app.model.journal import Journal
from src.app.service.property import PropertyService
from src.app.model.property import Property, PropertyTransaction, _PropertyPriceBrief

router = APIRouter(prefix="/property", tags=["property"])

@router.post("/property/validate_property")
def validate_property(property: Property) -> Property:
    return PropertyService._validate_property(property)
    
@router.get(
    "/property/trial_journal",
    description='use to generate journal during new property creation'
)
def create_journal_from_new_property(property: Property) -> Journal:
    return PropertyService.create_journal_from_property(property)

@router.get(
    "/property/get_property_journal/{property_id}",
    description='get existing property and journal from database'
)
def get_property_journal(property_id: str) -> Tuple[Property, Journal]:
    return PropertyService.get_property_journal(property_id=property_id)

@router.get("/property/list")
def list_property() -> list[Property]:
    return PropertyService.list_properties()

@router.get("/property/get_stat")
def get_acc_stat(property_id: str, rep_dt: date) -> _PropertyPriceBrief:
    return PropertyService.get_acc_stat(
        property_id=property_id,
        rep_dt=rep_dt
    )

@router.post("/property/add")
def add_property(property: Property):
    PropertyService.add_property(property=property)
    
@router.put("/property/update")
def update_property(property: Property):
    PropertyService.update_property(property=property)
    
@router.delete("/property/delete/{property_id}")
def delete_property(property_id: str):
    PropertyService.delete_property(property_id=property_id)
    
    
@router.post("/transaction/validate")
def validate_property_trans(property_trans: PropertyTransaction) -> PropertyTransaction:
    return PropertyService._validate_propertytrans(property_trans)
    
@router.get(
    "/transaction/trial_journal",
    description='use to generate journal during new property_trans creation'
)
def create_journal_from_new_property_trans(property_trans: PropertyTransaction) -> Journal:
    return PropertyService.create_journal_from_property_trans(property_trans)

@router.get(
    "/transaction/get_property_trans_journal/{trans_id}",
    description='get existing property_trans and journal from database'
)
def get_property_trans_journal(trans_id: str) -> Tuple[PropertyTransaction, Journal]:
    return PropertyService.get_property_trans_journal(trans_id=trans_id)

@router.get("/transaction/list")
def list_property_trans(property_id: str) -> list[PropertyTransaction]:
    return PropertyService.list_transactions(property_id)

@router.post("/transaction/add")
def add_property_trans(property_trans: PropertyTransaction):
    PropertyService.add_property_trans(property_trans=property_trans)
    
@router.put("/transaction/update")
def update_property_trans(property_trans: PropertyTransaction):
    PropertyService.update_property_trans(property_trans=property_trans)
    
@router.delete("/transaction/delete/{trans_id}")
def delete_property_trans(trans_id: str):
    PropertyService.delete_property_trans(trans_id=trans_id)
    