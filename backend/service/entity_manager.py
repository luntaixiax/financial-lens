import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from model.entity import Entity
from dao.entity import entityDao

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