from fastapi import APIRouter, Depends, Request
from src.app.model.enums import EntityType
from src.app.model.invoice import Item
from src.app.service.item import ItemService
from src.web.dependency.service import get_item_service

router = APIRouter(prefix="/item", tags=["item"])

@router.post("/add")
def add_item(
    item: Item, 
    item_service: ItemService = Depends(get_item_service)
):
    item_service.add_item(item=item)
    
@router.put("/update")
def update_item(
    item: Item, 
    item_service: ItemService = Depends(get_item_service)
):
    item_service.update_item(item=item)
    
@router.delete("/delete/{item_id}")
def delete_item(
    item_id: str, 
    item_service: ItemService = Depends(get_item_service)
):
    item_service.delete_item(item_id=item_id)
    
@router.get("/get/{item_id}")
def get_item(
    item_id: str, 
    item_service: ItemService = Depends(get_item_service)
) -> Item:
    return item_service.get_item(item_id=item_id)

@router.get("/list")
def list_item(
    entity_type: EntityType, 
    item_service: ItemService = Depends(get_item_service)
) -> list[Item]:
    return item_service.list_item(entity_type=entity_type)