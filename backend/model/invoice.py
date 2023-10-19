from typing import List, Dict
from dataclasses import dataclass
from enums import CurType
from datetime import datetime

@dataclass
class InvoiceItem:
    item_id: int # id of the invoice item
    desc: str # description
    unit_price: float
    quantity: int
    tax: float
    
    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity
    
@dataclass
class Invoice:
    invoice_id: str
    invoice_dt: datetime
    entity_id_provider: str  # who provide service and send invoice, should be from entity_id
    entity_id_payer: str # who receive service and pay bill, should be from entity_id
    currency: CurType
    items: List[InvoiceItem]
    discount: float = 0
    shipping: float = 0 # shipping or handling
    note: str = None
    
    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items) - self.discount
    
    @property
    def tax(self) -> float:
        return sum(item.tax for item in self.items)
    
    @property
    def total(self) -> float:
        return self.subtotal + self.tax + self.shipping
    
    
if __name__ == '__main__':
    
    i = Invoice(
        invoice_id='i-123',
        invoice_dt=datetime(2023, 10, 14, 9, 0, 0),
        entity_id_provider='e1234',
        entity_id_payer='c1234',
        currency=CurType.CAD,
        items = [
            InvoiceItem(
                item_id = 1,
                desc = 'macbook',
                unit_price = 150,
                quantity = 10,
                tax = 1.3
            ),
            InvoiceItem(
                item_id = 1,
                desc = 'shipping',
                unit_price = 10,
                quantity = 1,
                tax = 0
            )
        ]
    )
    print(i)

    

    