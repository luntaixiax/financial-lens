from fastapi import APIRouter, Request
from src.app.model.enums import EntityType
from src.app.model.invoice import Item
from src.app.service.item import ItemService

router = APIRouter(prefix="/item", tags=["item"])

@router.post("/item/add")
def add_item(item: Item):
    ItemService.add_item(item=item)
    
@router.put("/item/update")
def update_item(item: Item):
    ItemService.update_item(item=item)
    
@router.delete("/item/delete/{item_id}")
def delete_item(item_id: str):
    ItemService.delete_item(item_id=item_id)
    
@router.get("/item/get/{item_id}")
def get_item(item_id: str) -> Item:
    return ItemService.get_item(item_id=item_id)

@router.get("/item/list")
def list_item(entity_type: EntityType) -> list[Item]:
    return ItemService.list_item(entity_type=entity_type)