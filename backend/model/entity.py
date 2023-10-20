from typing import List, Dict, Union, Optional, ClassVar
from dataclasses import dataclass
from enums import EntityType
from datetime import datetime

@dataclass(kw_only=True)
class Address:
    address1: str
    address2: str | None = None
    suite_no: str | int | None = None
    city: str
    state: str
    country: str
    postal_code: str | int
    
    @property
    def address_line(self) -> str:
        adress_line = ""
        if self.suite_no is not None:
            adress_line += f"{self.suite_no} - "
        adress_line += self.address1
        if self.address2 is not None:
            adress_line += f", {self.address2}"
            
        return adress_line
            
    @property
    def post_code_line(self) -> str:
        return f"{self.city}, {self.state}, {self.country}, {self.postal_code}"

@dataclass(kw_only=True)
class Entity:
    entity_id: str = None
    name: str
    entity_type: EntityType
    email: str
    phone: str | None = None
    address: Address | None = None
    avatar: str | None = None # relative path of icon

# @dataclass(kw_only=True)
# class Person(Entity):
#     _type: ClassVar[str] = 'Person'
    
# @dataclass(kw_only=True)
# class Corporate(Entity):
#     _type: ClassVar[str] = 'Corporate'

# @dataclass(kw_only=True)
# class Employee(Entity):
#     _type: ClassVar[str] = 'Employee'
#     position: str
#     role: RoleType

# @dataclass(kw_only=True)
# class Client(Entity):
#     _type: ClassVar[str] = 'Client'

# @dataclass(kw_only=True)
# class Vendor(Entity):
#     _type: ClassVar[str] = 'Vendor'
    
# @dataclass(kw_only=True)
# class ShareHolder(Entity):
#     _type: ClassVar[str] = 'ShareHolder'
#     share: float = 1
    
# @dataclass(kw_only=True)
# class Lender(Entity):
#     _type: ClassVar[str] = 'Lender'

if __name__ == '__main__':
    from dacite import from_dict, Config
    from enum import Enum
    
    # a = Address(
    #     **{
    #         'address1' : '33 Charles st E',
    #         'suite_no' : 1603,
    #         'city' : 'Toronto',
    #         'state' : 'Ontario',
    #         'country' : 'Canada',
    #         'postal_code' : 'M4Y0A2'
    #     }
    # )
    a = from_dict(
        data_class = Address,
        data = {
            'address1' : '33 Charles st E',
            'suite_no' : 1603,
            'city' : 'Toronto',
            'state' : 'ON',
            'country' : 'Canada',
            'postal_code' : 'M4Y0A2'
        }
    )
    print(a)
    
    e1 = Entity(
        entity_id = 'e123',
        name = 'LTX',
        entity_type = EntityType.CORP,
        email = 'ltx@sss.com',
        address = a
    )
    print(e1.__dict__)
    
    # e2 = Entity(
    #     **{
    #         'entity_id' : 'e123',
    #         'name' : 'LTX',
    #         'entity_type' : EntityType.CORP,
    #         'email' : 'ltx@sss.com',
    #         'address' : Address(
    #             **{
    #                 'address1' : '33 Charles st E',
    #                 'suite_no' : 1603,
    #                 'city' : 'Toronto',
    #                 'state' : 'Ontario',
    #                 'country' : 'Canada',
    #                 'postal_code' : 'M4Y0A2'
    #             }
    #         )
    #     }
    # )
    e2 = from_dict(
        data_class = Entity,
        data = {
            'entity_id' : 'e123',
            'name' : 'LTX',
            'entity_type' : 2,
            'email' : 'ltx@sss.com',
            'address' : {
                'address1' : '33 Charles st E',
                'suite_no' : 1603,
                'city' : 'Toronto',
                'state' : 'Ontario',
                'country' : 'Canada',
                'postal_code' : 'M4Y0A2'
            }
        },
        config = Config(cast = [Enum])
    )
    print(e2.__dict__)
    print(e1 == e2)
    
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
    from dacite import from_dict, Config
    from enum import Enum
    from utils.tools import id_generator
    
    
    def create_person(name: str, email: str, phone: str = None, address_dict: dict = None) -> Entity:
        data_dict = dict(
            entity_id = id_generator(prefix = 'e-', length = 5),
            name = name,
            entity_type = 1, # 1 is personal
            email = email,
            phone = phone,
            address = address_dict
        )
        person = from_dict(
            data_class = Entity,
            data = data_dict,
            config = Config(cast = [Enum])
        )
        return person
    
    person = create_person(
        name = 'ltx',
        email= 'ltx@gmail.com',
        address_dict = {
            'address1' : '33 Charles st E',
            'suite_no' : 1603,
            'city' : 'Toronto',
            'state' : 'Ontario',
            'country' : 'Canada',
            'postal_code' : 'M4Y0A2'
        }
    )
    print(person)
    print(a.address_line)
    print(a.post_code_line)