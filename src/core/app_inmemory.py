from __future__ import annotations
# Habilita anotações de tipo “adiadas”, útil para compatibilidade e organização.

from typing import Optional
# Optional[str] é usado para armazenar session_id/user_id que podem começar como None.

import time
# Usado para simular latências (futuro: cache/Redis/Cassandra etc.).

from core.ports import SessionStore, EventStore, MetricsStore, Product, CartStore
# Importa os PORTS (contratos) e alguns modelos do domínio.
# Note que a App depende de interfaces (SessionStore, EventStore, MetricsStore, CartStore),
# e não de implementações concretas (Redis/InMemory) — isso é Ports & Adapters na prática.

from core.util import Timer, money, new_id
# Timer: mede tempo para gerar métricas de latência
# money: formata valores monetários
# new_id: gera IDs simples (ord-xxxx, etc.)

from services.catalog_service import CatalogService
from services.cart_service import CartService
from services.session_service import SessionService
from services.event_service import EventService
from services.metrics_service import MetricsService
# Serviços do core: encapsulam regras e padronizam o acesso aos stores.
# A App (CLI) é “camada de orquestração”: lê input, chama serviços, imprime output.


class MiniShopApp:
    def __init__(
        self,
        session_store: SessionStore,
        event_store: EventStore,
        metrics_store: MetricsStore,
        cart_store: CartStore
    ):
        # Aqui a App injeta os adapters (implementações) via os PORTS.
        # A App não sabe se session_store é Redis ou InMemory, por exemplo.
        self.session_svc = SessionService(session_store)
        self.event_svc = EventService(event_store)
        self.metrics_svc = MetricsService(metrics_store)

        # Catálogo permanece “fixo” (didático) e local por enquanto.
        self.catalog = CatalogService()

        # Evolução importante:
        # Antes: CartService() mantinha apenas estado em memória.
        # Agora: CartService(cart_store) persiste e recupera carrinho via port CartStore.
        self.cart = CartService(cart_store)

        # Estado da sessão atual na CLI
        self.current_session_id: Optional[str] = None
        self.current_user_id: Optional[str] = None

    # -------------------------
    # CLI
    # -------------------------
    def run_cli(self):
        # Loop principal da aplicação CLI: menu -> ação -> volta ao menu.
        self._print_banner()
        while True:
            self._print_menu()
            choice = input("Escolha: ").strip()

            # Dispatch de comandos
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
                # Encerra a CLI
                print("Saindo. Até mais!")
                return
            else:
                print("Opção inválida.")

    def _print_banner(self):
        # Mensagem inicial. Dá contexto do curso e do roadmap.
        print("\n===================================")
        print(" MiniShop CLI (Usando NOSQL)")
        print(" Redis -> implementado | Mongo -> depois | Cassandra -> depois")
        print("===================================\n")

    def _print_menu(self):
        # Menu textual da CLI
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
        # Guardrail: garante que existe uma sessão válida antes de executar ações sensíveis.
        # self.session_svc.current() verifica a sessão atual (em Redis ou InMemory).
        sess = self.session_svc.current(self.current_session_id)
        if not sess:
            print("Você precisa fazer login primeiro.")
            return False
        return True

    # -------------------------
    # Actions
    # -------------------------
    def login(self):
        # Login da CLI:
        # 1) cria/retoma sessão via SessionService (que delega para SessionStore)
        # 2) associa o carrinho à sessão e carrega do store (CartStore)
        # 3) registra evento e métricas
        user_id = input("User ID (ex: u123): ").strip() or "u123"

        sess = self.session_svc.login(user_id)
        self.current_session_id = sess.session_id
        self.current_user_id = sess.user_id

        # OBS: a linha abaixo estava comentada (e é correto ter removido),
        # porque agora clear() poderia apagar o carrinho persistido.
        # self.cart.clear()

        # ⚠️ Importante: a ordem correta aqui é:
        #   1) bind_session()
        #   2) depois imprimir count_items/total
        #
        # Do jeito que está neste trecho, você imprime antes de carregar.
        # O certo seria:
        #   self.cart.bind_session(sess.session_id)
        #   print(...)
        print(f"Carrinho recuperado: itens={self.cart.count_items()} total=€ {money(self.cart.total())}")
        self.cart.bind_session(sess.session_id)

        # Emite evento de login (hoje in-memory; depois MongoDB/event log)
        self.event_svc.emit(
            "user_login",
            sess.user_id,
            sess.session_id,
            {"created_at": sess.created_at.isoformat()}
        )

        # Incrementa contador de logins (hoje in-memory; depois pode ir para Cassandra)
        self.metrics_svc.inc("logins", 1)

        print(f"Login OK. session_id={sess.session_id}")

    def view_catalog(self):
        # Lista o catálogo:
        # - mede tempo (latência)
        # - simula custo com sleep (depois pode virar cache Redis)
        with Timer() as t:
            time.sleep(0.15)
            products = self.catalog.list_all()

        self.metrics_svc.latency("view_catalog", t.elapsed_ms)
        self.metrics_svc.inc("catalog_views", 1)

        print("\n--- Catálogo ---")
        for p in products:
            print(f"- {p.sku} | {p.name} | {p.category} | € {money(p.price)}")

        # Se tiver sessão, registra evento
        if self.current_session_id and self.current_user_id:
            self.event_svc.emit(
                "view_catalog",
                self.current_user_id,
                self.current_session_id,
                {"count": len(products)}
            )

    def view_product(self):
        # Exige login para ver detalhe (decisão didática; poderia ser público).
        if not self._require_login():
            return

        sku = input("SKU (ex: A100): ").strip().upper() or "A100"

        with Timer() as t:
            time.sleep(0.10)
            product = self.catalog.get_by_sku(sku)

        self.metrics_svc.latency("view_product", t.elapsed_ms)
        self.metrics_svc.inc("product_views", 1)

        if not product:
            print("Produto não encontrado.")
            self.event_svc.emit(
                "view_product_not_found",
                self.current_user_id,
                self.current_session_id,
                {"sku": sku}
            )
            self.metrics_svc.inc("product_not_found", 1)
            return

        print(f"\nProduto: {product.sku} | {product.name}")
        print(f"Categoria: {product.category}")
        print(f"Preço: € {money(product.price)}")

        self.event_svc.emit(
            "view_product",
            self.current_user_id,
            self.current_session_id,
            {"sku": product.sku, "price": product.price}
        )

    def search_product(self):
        # Busca no catálogo:
        # - simula latência
        # - gera métricas e evento
        query = input("Buscar por (nome/categoria/SKU): ").strip()
        with Timer() as t:
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
            self.event_svc.emit(
                "search_product",
                self.current_user_id,
                self.current_session_id,
                {"query": query, "results": len(results)}
            )

    def add_to_cart(self):
        # Adiciona ao carrinho:
        # - valida login
        # - valida SKU
        # - chama CartService.add() (que agora persiste em CartStore)
        if not self._require_login():
            return

        sku = input("SKU para adicionar: ").strip().upper() or "A100"
        qty_raw = input("Qtd (default=1): ").strip()
        qty = int(qty_raw) if qty_raw.isdigit() and int(qty_raw) > 0 else 1

        product = self.catalog.get_by_sku(sku)
        if not product:
            print("Produto não encontrado.")
            self.event_svc.emit(
                "add_to_cart_failed",
                self.current_user_id,
                self.current_session_id,
                {"sku": sku}
            )
            self.metrics_svc.inc("add_to_cart_failed", 1)
            return

        # Aqui é onde a persistência “acontece”:
        # CartService.add() atualiza a lista local e chama _persist(),
        # o que grava no Redis/InMemory dependendo do adapter ativo.
        self.cart.add(product, qty)
        self.metrics_svc.inc("adds_to_cart", 1)

        print(f"Adicionado: {product.sku} x{qty}")
        print(f"Itens no carrinho: {self.cart.count_items()} | Total: € {money(self.cart.total())}")

        self.event_svc.emit(
            "add_to_cart",
            self.current_user_id,
            self.current_session_id,
            {
                "sku": product.sku,
                "qty": qty,
                "cart_items": self.cart.count_items(),
                "cart_total": self.cart.total(),
            }
        )

    def view_cart(self):
        # Exibe o carrinho atual (estado local já carregado/persistido via CartService)
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
        self.event_svc.emit(
            "view_cart",
            self.current_user_id,
            self.current_session_id,
            {
                "cart_items": self.cart.count_items(),
                "cart_total": self.cart.total(),
            }
        )

    def remove_from_cart(self):
        # Remove do carrinho:
        # - valida login
        # - chama CartService.remove() que persiste após remover
        if not self._require_login():
            return

        sku = input("SKU para remover: ").strip().upper()
        qty_raw = input("Qtd para remover (default=1): ").strip()
        qty = int(qty_raw) if qty_raw.isdigit() and int(qty_raw) > 0 else 1

        ok = self.cart.remove(sku, qty)
        if not ok:
            print("Item não encontrado no carrinho.")
            self.metrics_svc.inc("remove_from_cart_failed", 1)
            self.event_svc.emit(
                "remove_from_cart_failed",
                self.current_user_id,
                self.current_session_id,
                {"sku": sku, "qty": qty}
            )
            return

        self.metrics_svc.inc("removes_from_cart", 1)
        print(f"Removido: {sku} x{qty}")
        print(f"Itens no carrinho: {self.cart.count_items()} | Total: € {money(self.cart.total())}")

        self.event_svc.emit(
            "remove_from_cart",
            self.current_user_id,
            self.current_session_id,
            {
                "sku": sku,
                "qty": qty,
                "cart_items": self.cart.count_items(),
                "cart_total": self.cart.total(),
            }
        )

    def checkout(self):
        # Checkout:
        # - valida login
        # - valida carrinho não vazio
        # - simula processamento
        # - registra métricas/eventos
        # - limpa carrinho (e no modelo atual, isso também apaga a chave no CartStore)
        if not self._require_login():
            return

        if self.cart.is_empty():
            print("Carrinho vazio. Nada para fechar.")
            self.metrics_svc.inc("checkout_failed_empty_cart", 1)
            self.event_svc.emit(
                "checkout_failed",
                self.current_user_id,
                self.current_session_id,
                {"reason": "empty_cart"}
            )
            return

        with Timer() as t:
            time.sleep(0.18)
            total = self.cart.total()
            items = self.cart.count_items()
            order_id = new_id("ord")

        self.metrics_svc.latency("checkout", t.elapsed_ms)
        self.metrics_svc.inc("checkouts", 1)

        self.event_svc.emit(
            "checkout_success",
            self.current_user_id,
            self.current_session_id,
            {"order_id": order_id, "total": total, "items": items}
        )

        print("\n✅ Checkout concluído!")
        print(f"Pedido: {order_id}")
        print(f"Itens: {items}")
        print(f"Total: € {money(total)}")

        # Limpa o carrinho: em Redis isso normalmente vira DEL cart:<session_id>
        self.cart.clear()

    def show_events(self):
        # Exibe últimos eventos (hoje: store in-memory; depois: MongoDB)
        events = self.event_svc.tail(12)
        print("\n--- Eventos recentes ---")
        if not events:
            print("(nenhum evento)")
            return
        for e in events:
            print(f"{e.ts.isoformat()} | {e.event_type} | user={e.user_id} | sess={e.session_id} | {e.payload}")

    def show_metrics(self):
        # Exibe métricas e contadores (hoje: store in-memory; depois: Cassandra/TS)
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
