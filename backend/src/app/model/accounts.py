from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from functools import partial
from anytree import NodeMixin, Node, RenderTree, find_by_attr
from src.app.model.enums import AcctType, CurType, BankAcctType
from src.app.utils.tools import id_generator
from src.app.utils.base import EnhancedBaseModel

class Chart(EnhancedBaseModel):
    chart_id: str = Field(
        default_factory=partial(
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
            
    def find_node_by_name(self, chart_name: str) -> ChartNode:
        return find_by_attr(self, chart_name, name='name')
    
    def find_node_by_id(self, chart_id: str) -> ChartNode:
        return find_by_attr(self, chart_id, name='chart_id')
            
            
class Account(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    acct_id: str = Field(
        default_factory=partial(
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