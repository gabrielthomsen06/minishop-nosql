from __future__ import annotations
from typing import Optional
import time

from core.ports import SessionStore, EventStore, MetricsStore, Product, CartStore
from core.util import Timer, money, new_id
from services.catalog_service import CatalogService
from services.cart_service import CartService
from services.session_service import SessionService
from services.event_service import EventService
from services.metrics_service import MetricsService

class MiniShopApp:
    def __init__(self, session_store: SessionStore, event_store: EventStore, metrics_store: MetricsStore, cart_store: CartStore):
        self.session_svc = SessionService(session_store)
        self.event_svc = EventService(event_store)
        self.metrics_svc = MetricsService(metrics_store)
        self.catalog = CatalogService()
        # self.cart = CartService()
        self.cart = CartService(cart_store)

        self.current_session_id: Optional[str] = None
        self.current_user_id: Optional[str] = None

    # -------------------------
    # CLI
    # -------------------------
    def run_cli(self):
        self._print_banner()
        while True:
            self._print_menu()
            choice = input("Escolha: ").strip()
            if choice == "1":
                self.login()
            elif choice == "2":
                self.view_catalog()
            elif choice == "3":
                self.view_product()
            elif choice == "4":
                self.search_product()
            elif choice == "5":
                self.add_to_cart()
            elif choice == "6":
                self.view_cart()
            elif choice == "7":
                self.remove_from_cart()
            elif choice == "8":
                self.checkout()
            elif choice == "9":
                self.show_events()
            elif choice == "10":
                self.show_metrics()
            elif choice == "0":
                if self.current_session_id:
                    self.event_svc.clear_session(self.current_session_id)
                    self.session_svc.logout(self.current_session_id)
                print("Saindo. Até mais!")
                return
            else:
                print("Opção inválida.")

    def _print_banner(self):
        print("\n===================================")
        print(" MiniShop CLI (Usando NOSQL)")
        print(" Redis -> implementado | Mongo -> implementado | Cassandra -> depois")
        print("===================================\n")

    def _print_menu(self):
        print("\n=== MENU ===")
        print("1) Login")
        print("2) Ver catálogo")
        print("3) Ver detalhes de produto")
        print("4) Buscar produto")
        print("5) Adicionar ao carrinho")
        print("6) Ver carrinho")
        print("7) Remover do carrinho")
        print("8) Checkout")
        print("9) Ver eventos recentes")
        print("10) Ver métricas & contadores")
        print("0) Sair")

    def _require_login(self) -> bool:
        sess = self.session_svc.current(self.current_session_id)
        if not sess:
            print("Você precisa fazer login primeiro.")
            return False
        return True

    # -------------------------
    # Actions
    # -------------------------
    def login(self):
        user_id = input("User ID (ex: u123): ").strip() or "u123"
        sess = self.session_svc.login(user_id)

        self.current_session_id = sess.session_id
        self.current_user_id = sess.user_id

        # PRIMEIRO: ligar o carrinho à sessão (carrega do Redis)
        self.cart.bind_session(sess.session_id)

        # AGORA SIM: o carrinho já está carregado
        print(f"Carrinho recuperado: itens={self.cart.count_items()} total=€ {money(self.cart.total())}")

        self.event_svc.emit(
            "user_login",
            sess.user_id,
            sess.session_id,
            {"created_at": sess.created_at.isoformat()}
        )
        self.metrics_svc.inc("logins", 1)

        print(f"Login OK. session_id={sess.session_id}")

    def view_catalog(self):
        with Timer() as t:
            # simula custo (depois vira cache Redis)
            time.sleep(0.15)
            products = self.catalog.list_all()

        self.metrics_svc.latency("view_catalog", t.elapsed_ms)
        self.metrics_svc.inc("catalog_views", 1)

        print("\n--- Catálogo ---")
        for p in products:
            print(f"- {p.sku} | {p.name} | {p.category} | € {money(p.price)}")

        if self.current_session_id and self.current_user_id:
            self.event_svc.emit("view_catalog", self.current_user_id, self.current_session_id, {"count": len(products)})

    def view_product(self):
        if not self._require_login():
            return
        sku = input("SKU (ex: A100): ").strip().upper() or "A100"

        with Timer() as t:
            # simula custo (depois vira cache Redis por SKU)
            time.sleep(0.10)
            product = self.catalog.get_by_sku(sku)

        self.metrics_svc.latency("view_product", t.elapsed_ms)
        self.metrics_svc.inc("product_views", 1)

        if not product:
            print("Produto não encontrado.")
            self.event_svc.emit("view_product_not_found", self.current_user_id, self.current_session_id, {"sku": sku})
            self.metrics_svc.inc("product_not_found", 1)
            return

        print(f"\nProduto: {product.sku} | {product.name}")
        print(f"Categoria: {product.category}")
        print(f"Preço: € {money(product.price)}")

        self.event_svc.emit("view_product", self.current_user_id, self.current_session_id, {
            "sku": product.sku, "price": product.price
        })

    def search_product(self):
        query = input("Buscar por (nome/categoria/SKU): ").strip()
        with Timer() as t:
            # simula custo (depois pode virar cache Redis por query)
            time.sleep(0.12)
            results = self.catalog.search(query)

        self.metrics_svc.latency("search_product", t.elapsed_ms)
        self.metrics_svc.inc("searches", 1)

        print("\n--- Resultados ---")
        if not results:
            print("(nenhum resultado)")
        else:
            for p in results:
                print(f"- {p.sku} | {p.name} | {p.category} | € {money(p.price)}")

        if self.current_session_id and self.current_user_id:
            self.event_svc.emit("search_product", self.current_user_id, self.current_session_id, {
                "query": query, "results": len(results)
            })

    def add_to_cart(self):
        if not self._require_login():
            return
        sku = input("SKU para adicionar: ").strip().upper() or "A100"
        qty_raw = input("Qtd (default=1): ").strip()
        qty = int(qty_raw) if qty_raw.isdigit() and int(qty_raw) > 0 else 1

        product = self.catalog.get_by_sku(sku)
        if not product:
            print("Produto não encontrado.")
            self.event_svc.emit("add_to_cart_failed", self.current_user_id, self.current_session_id, {"sku": sku})
            self.metrics_svc.inc("add_to_cart_failed", 1)
            return

        self.cart.add(product, qty)
        self.metrics_svc.inc("adds_to_cart", 1)

        print(f"Adicionado: {product.sku} x{qty}")
        print(f"Itens no carrinho: {self.cart.count_items()} | Total: € {money(self.cart.total())}")

        self.event_svc.emit("add_to_cart", self.current_user_id, self.current_session_id, {
            "sku": product.sku,
            "qty": qty,
            "cart_items": self.cart.count_items(),
            "cart_total": self.cart.total()
        })

    def view_cart(self):
        if not self._require_login():
            return
        items = self.cart.items()
        print("\n--- Carrinho ---")
        if not items:
            print("(vazio)")
            return
        for i in items:
            line_total = i.unit_price * i.qty
            print(f"- {i.sku} | {i.name} | € {money(i.unit_price)} x {i.qty} = € {money(line_total)}")
        print(f"Total: € {money(self.cart.total())} | Itens: {self.cart.count_items()}")

        self.metrics_svc.inc("cart_views", 1)
        self.event_svc.emit("view_cart", self.current_user_id, self.current_session_id, {
            "cart_items": self.cart.count_items(),
            "cart_total": self.cart.total()
        })

    def remove_from_cart(self):
        if not self._require_login():
            return
        sku = input("SKU para remover: ").strip().upper()
        qty_raw = input("Qtd para remover (default=1): ").strip()
        qty = int(qty_raw) if qty_raw.isdigit() and int(qty_raw) > 0 else 1

        ok = self.cart.remove(sku, qty)
        if not ok:
            print("Item não encontrado no carrinho.")
            self.metrics_svc.inc("remove_from_cart_failed", 1)
            self.event_svc.emit("remove_from_cart_failed", self.current_user_id, self.current_session_id, {"sku": sku, "qty": qty})
            return

        self.metrics_svc.inc("removes_from_cart", 1)
        print(f"Removido: {sku} x{qty}")
        print(f"Itens no carrinho: {self.cart.count_items()} | Total: € {money(self.cart.total())}")

        self.event_svc.emit("remove_from_cart", self.current_user_id, self.current_session_id, {
            "sku": sku,
            "qty": qty,
            "cart_items": self.cart.count_items(),
            "cart_total": self.cart.total()
        })

    def checkout(self):
        if not self._require_login():
            return
        if self.cart.is_empty():
            print("Carrinho vazio. Nada para fechar.")
            self.metrics_svc.inc("checkout_failed_empty_cart", 1)
            self.event_svc.emit("checkout_failed", self.current_user_id, self.current_session_id, {"reason": "empty_cart"})
            return

        with Timer() as t:
            # simula processamento (pagamento / pedido)
            time.sleep(0.18)
            total = self.cart.total()
            items = self.cart.count_items()
            order_id = new_id("ord")

        self.metrics_svc.latency("checkout", t.elapsed_ms)
        self.metrics_svc.inc("checkouts", 1)

        self.event_svc.emit("checkout_success", self.current_user_id, self.current_session_id, {
            "order_id": order_id,
            "total": total,
            "items": items
        })

        print("\n✅ Checkout concluído!")
        print(f"Pedido: {order_id}")
        print(f"Itens: {items}")
        print(f"Total: € {money(total)}")
        self.cart.clear()

    def show_events(self):
        if not self._require_login():
            return
        events = self.event_svc.tail(12, session_id=self.current_session_id)
        print("\n--- Eventos desta sessão ---")
        if not events:
            print("(nenhum evento)")
            return
        for e in events:
            print(f"{e.ts.isoformat()} | {e.event_type} | {e.payload}")

    def show_metrics(self):
        pts = self.metrics_svc.latest(12)
        counters = self.metrics_svc.counters()

        print("\n--- Métricas recentes ---")
        if not pts:
            print("(nenhuma métrica)")
        else:
            for p in pts:
                print(f"{p.ts.isoformat()} | {p.metric}={p.value:.2f} | tags={p.tags}")

        print("\n--- Contadores (snapshot) ---")
        if not counters:
            print("(vazio)")
        else:
            for k, v in sorted(counters.items()):
                print(f"- {k}: {v}")

