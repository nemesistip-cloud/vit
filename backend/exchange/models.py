from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    wallet_id: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    remaining_quantity: Decimal = field(init=False)

    def __post_init__(self):
        self.remaining_quantity = self.quantity

@dataclass
class Trade:
    buyer_wallet_id: str
    seller_wallet_id: str
    price: Decimal
    quantity: Decimal
    buy_order_id: str
    sell_order_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
