from __future__ import annotations
from typing import List, Optional
from core.ports import CartItem, Product

class CartService:
    def __init__(self):
        self._items: List[CartItem] = []

    def items(self) -> List[CartItem]:
        return list(self._items)

    def add(self, product: Product, qty: int = 1) -> None:
        if qty <= 0:
            return
        existing = next((i for i in self._items if i.sku == product.sku), None)
        if existing:
            existing.qty += qty
        else:
            self._items.append(CartItem(
                sku=product.sku,
                name=product.name,
                unit_price=product.price,
                qty=qty
            ))

    def remove(self, sku: str, qty: int = 1) -> bool:
        sku = sku.strip().upper()
        item = next((i for i in self._items if i.sku == sku), None)
        if not item:
            return False
        if qty <= 0:
            return False
        item.qty -= qty
        if item.qty <= 0:
            self._items = [i for i in self._items if i.sku != sku]
        return True

    def clear(self) -> None:
        self._items = []

    def total(self) -> float:
        return sum(i.unit_price * i.qty for i in self._items)

    def count_items(self) -> int:
        return sum(i.qty for i in self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0
