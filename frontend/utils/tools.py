from typing import Any
from pydantic import BaseModel
from bidict import bidict

class DropdownSelect:
    def __init__(self, briefs: list[dict | BaseModel], include_null: bool, id_key: str, display_keys: list[str] | None = None):
        self._briefs = briefs
        self._idkey = id_key
        self._displaykeys = display_keys or [id_key]
        self._include_null = include_null
        
        self._mappings = bidict({
            b[id_key]: self._display_single(b)
            for b in self._briefs
        })
        
    def _display_single(self, brief: dict | BaseModel) -> str:
        # how to display in options
        s = " | "
        return s.join(str(brief[key]) for key in self._displaykeys)
    
    @property
    def options(self) -> list[str | None]:
        ops = list(self._mappings.values())
        if self._include_null:
            ops.insert(0, None)
        return ops
    
    def get_id(self, option: str | None) -> str | None:
        if self._include_null:
            if option is None:
                return None
        return self._mappings.inverse[option]
    
    def get_idx_from_option(self, option: str | None) -> int:
        if self._include_null:
            if option is None:
                return 0
        return self.options.index(option)
    
    def get_idx_from_id(self, id_: str) -> int:
        idx = list(self._mappings.keys()).index(id_)
        if self._include_null:
            idx += 1
        return idx
    
    @classmethod
    def from_enum(cls, enum_cls, include_null: bool):
        return DropdownSelect(
            briefs = [
                {
                    'name': e.name,
                    'value': e
                }
                for e in enum_cls
            ],
            include_null = include_null,
            id_key = 'value',
            display_keys = ['name']
        )
        
        
def display_number(x: float | None) -> str:
    if x is None:
        return '-'
    if x == 0:
        return '-'
    else:
        return f"{x:,.2f}"