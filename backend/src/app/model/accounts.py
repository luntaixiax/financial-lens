from __future__ import annotations
from typing import Any, Literal
from pydantic import computed_field, ConfigDict, Field, model_validator
from functools import partial
from anytree import NodeMixin, Node, RenderTree, find_by_attr
from anytree.exporter import DictExporter
from anytree.importer import DictImporter
from src.app.model.const import SystemAcctNumber
from src.app.model.enums import AcctType, CurType, BankAcctType
from src.app.utils.tools import id_generator
from src.app.utils.base import EnhancedBaseModel

class Chart(EnhancedBaseModel):
    chart_id: str = Field(
        default_factory=partial( # type: ignore
            id_generator,
            prefix='choa-',
            length=8,
        ),
        frozen=True,
    )
    name: str
    acct_type: AcctType



class ChartNode(NodeMixin):
    def __init__(self, chart: Chart, parent=None, children=None):
        super().__init__()
        self.name = chart.name
        self.chart_id = chart.chart_id
        self.chart = chart
        
        self.parent = parent
        if children:
            self.children = children
        
    def _pre_attach(self, parent):
        # validation before attach
        if parent:
            assert parent.chart.acct_type == self.chart.acct_type, \
                f"Current chart acct type: {self.chart.acct_type} must match parent chart acct type: {parent.chart.acct_type}"
                
    def _extract_simple(self, attrs):
        extracted = []
        for k, v in attrs:
            if k == 'chart_id':
                extracted.append((k, v))
            elif k == 'chart':
                extracted.append(('name', v.name))
                #extracted.append(('acct_type', v.acct_type))
            else:
                pass
        return extracted
    
    def print(self):
        for pre, fill, node in RenderTree(self):
            print(f"{pre}{node.chart_id}({node.name})")
    
    def to_dict(self, simple: bool = False) -> dict[str, Any]:
        if simple:
            exporter = DictExporter(attriter = self._extract_simple)
        else:
            exporter = DictExporter()
        return exporter.export(self)
    
    @classmethod
    def from_dict(cls, node_dict: dict[str, Any]):
        # TODO: return is AnyNode, not original ChartNode dtype
        importer = DictImporter()
        return importer.import_(node_dict)
        
            
    def find_node_by_name(self, chart_name: str) -> ChartNode:
        return find_by_attr(self, chart_name, name='name') # type: ignore
    
    def find_node_by_id(self, chart_id: str) -> ChartNode:
        return find_by_attr(self, chart_id, name='chart_id') # type: ignore
            
            
class Account(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    acct_id: str = Field(
        default_factory=partial( # type: ignore
            id_generator,
            prefix='acct-',
            length=8,
        ),
        frozen=True,
    )
    acct_name: str
    acct_type: AcctType
    currency: CurType | None = Field(
        None,
        frozen=True
    )
    chart: Chart
    
    @computed_field()
    def is_system(self) -> bool:
        return self.acct_id in SystemAcctNumber.list_()
    
    @model_validator(mode='after')
    def validate_chart(self):
        assert self.acct_type == self.chart.acct_type, \
            f"Account type: {self.acct_type} must match chart account type: {self.chart.acct_type}"
        return self
    
    @model_validator(mode='after')
    def validate_fx(self):
        if self.acct_type in [AcctType.INC, AcctType.EXP]:
            assert self.currency is None, \
                f"This is Inc/Exp account, should not specify currency: {self.currency}"
        else:
            assert self.currency is not None, \
                f"This is Balance Sheet account, must specify currency"
        return self

    @property
    def is_balance_sheet(self) -> bool:
        return not (self.acct_type in (AcctType.INC, AcctType.EXP))