import logging
from typing import Dict, List
from dacite import from_dict, Config
from enum import Enum
from dataclasses import asdict
from sqlmodel import Session, select
from src.dao.orm import EntityORM
from src.dao.connection import engine
from src.model.entity import Entity
from src.utils.exceptions import DuplicateEntryError
from src.utils.tools import get_abs_img_path

class entityDao:
    @classmethod
    def fromEntity(cls, entity: Entity) -> EntityORM:
        return EntityORM(
            **asdict(entity)
        )
    
    @classmethod
    def toEntity(cls, entity_orm: EntityORM) -> Entity:
        entity_orm.phone = str(entity_orm.phone) # TODO: verify this
        return from_dict(
            data_class = Entity,
            data = entity_orm.dict(),
            config = Config(cast = [Enum])
        )
        
    @classmethod
    def add(cls, entity: Entity):
        entity_orm = cls.fromEntity(entity)
        with Session(engine) as s:
            # check unique
            sql = select(EntityORM).where(EntityORM.name == entity_orm.name)
            existing = s.exec(sql).all()
            if len(existing) > 0:
                raise DuplicateEntryError(f"name: {entity_orm.name} already exists")
            else:
                s.add(entity_orm)
                s.commit()
                logging.info(f"Added {entity_orm} to Entity table")
    
    @classmethod
    def remove(cls, entity_id: str):
        with Session(engine) as s:
            sql = select(EntityORM).where(EntityORM.entity_id == entity_id)
            p = s.exec(sql).one() # get the entity
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Entity table")
    
    @classmethod
    def update(cls, entity: Entity):
        entity_orm = cls.fromEntity(entity)
        with Session(engine) as s:
            sql = select(EntityORM).where(EntityORM.entity_id == entity_orm.entity_id)
            p = s.exec(sql).one() # get the entity
            
            # update
            p.name = entity_orm.name
            p.entity_type = entity_orm.entity_type
            p.email = entity_orm.email
            p.phone = entity_orm.phone
            p.address = entity_orm.address
            p.avatar = entity_orm.avatar
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Entity table")
    
    @classmethod
    def get(cls, entity_id: str) -> Entity:
        with Session(engine) as s:
            sql = select(EntityORM).where(EntityORM.entity_id == entity_id)
            p = s.exec(sql).one() # get the entity
        entity = cls.toEntity(p)
        return entity

    @classmethod
    def getIds(cls) -> List[str]:
        with Session(engine) as s:
            sql = select(EntityORM.entity_id)
            ps = s.exec(sql).all()
        return ps

    @classmethod
    def getNames(cls) -> List[str]:
        with Session(engine) as s:
            sql = select(EntityORM.name)
            ps = s.exec(sql).all()
        return ps
    
    @classmethod
    def get_avatar_abs_path(cls, entity_id: str) -> str:
        entity = cls.get(entity_id=entity_id)
        return get_abs_img_path(
            img_name = entity.avatar,
            sector = 'avatars'
        )


if __name__ == '__main__':
    # entity = from_dict(
    #     data_class = Entity,
    #     data = {
    #         'entity_id' : 'e123',
    #         'name' : 'LTX Intelligent Service Inc.',
    #         'entity_type' : 2,
    #         'email' : 'luntaix@ltxservice.ca',
    #         'address' : {
    #             'address1' : '33 Charles st E',
    #             'suite_no' : 1603,
    #             'city' : 'Toronto',
    #             'state' : 'Ontario',
    #             'country' : 'Canada',
    #             'postal_code' : 'M4Y0A2'
    #         },
    #         'avatar': 'LTX - logo.png'
    #     },
    #     config = Config(cast = [Enum])
    # )
    # entityDao.update(entity)
    
    # print(entityDao.getNames())
    print(entityDao.get('e-41ac6'))