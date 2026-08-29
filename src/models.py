from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class POItem:
    sku: str
    description: str
    quantity: float
    unit_price: float


@dataclass
class GRItem:
    sku: str
    quantity: float


@dataclass
class InvoiceItem:
    sku: str
    description: str
    quantity: float
    unit_price: float


@dataclass
class PurchaseOrder:
    po_id: str
    vendor: str
    items: List[POItem] = field(default_factory=list)
    currency: str = "USD"


@dataclass
class GoodsReceipt:
    receipt_id: str
    po_id: str
    received_items: List[GRItem] = field(default_factory=list)


@dataclass
class Invoice:
    invoice_id: str
    po_id: str
    vendor: str
    items: List[InvoiceItem] = field(default_factory=list)
    subtotal: float = 0.0
    currency: str = "USD"
