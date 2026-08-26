from __future__ import annotations
from typing import List, Optional
from core.ports import Product

class CatalogService:
    def __init__(self):
        # Catálogo fixo (simples e didático)
        self._products: List[Product] = [
            Product("A100", "Teclado Mecânico", "Periféricos", 349.90),
            Product("B200", "Mouse Gamer", "Periféricos", 189.90),
            Product("C300", "Headset", "Áudio", 299.90),
            Product("D400", "SSD 1TB", "Armazenamento", 499.90),
            Product("E500", "Monitor 27", "Monitores", 1299.90),
            Product("F600", "Webcam Full HD", "Acessórios", 239.90),
        ]

    def list_all(self) -> List[Product]:
        return list(self._products)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        sku = sku.strip().upper()
        return next((p for p in self._products if p.sku == sku), None)

    def search(self, query: str) -> List[Product]:
        q = query.strip().lower()
        if not q:
            return []
        return [p for p in self._products if q in p.name.lower() or q in p.category.lower() or q in p.sku.lower()]
