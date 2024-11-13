from legacy.model.entity import Entity
from legacy.dao.entity import entityDao

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