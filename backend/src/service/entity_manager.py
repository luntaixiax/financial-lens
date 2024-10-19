from src.model.entity import Entity
from src.dao.entity import entityDao

class EntityManager:
    @classmethod
    def create(cls, entity: Entity):
        entityDao.add(entity)
        
    @classmethod
    def update(cls, entity: Entity):
        entityDao.update(entity)
        
    @classmethod
    def delete(cls, entity_id: str):
        entityDao.remove(entity_id=entity_id)