from __future__ import annotations
# Permite usar anotações de tipo como "list[CartItem]" em versões antigas do Python,
# e evita alguns problemas de referência circular em type hints.

from typing import List
# Importa o tipo genérico List para tipagem (listas de CartItem).

from core.ports import CartItem, CartStore
# Importa:
# - CartItem: o modelo de item do carrinho (sku, nome, preço unitário, qty)
# - CartStore: o PORT (contrato) que define as operações que um storage de carrinho deve oferecer.


class InMemoryCartStore(CartStore):
    # Adapter (implementação concreta) do port CartStore.
    # Objetivo didático:
    # - permitir que o core use persistência de carrinho SEM Redis ainda
    # - provar a ideia "Port = contrato / Adapter = implementação"
    # - manter o comportamento previsível em testes locais

    def __init__(self):
        # Estrutura interna:
        # - chave: session_id (string)
        # - valor: lista de CartItem daquela sessão
        #
        # Esse dicionário simula um "banco" em memória.
        # Importante: os dados duram apenas enquanto o processo roda.
        self._data: dict[str, List[CartItem]] = {}

    def load(self, session_id: str) -> List[CartItem]:
        # Carrega o carrinho associado ao session_id.
        #
        # Regra do port:
        # - se não existir carrinho, retorna lista vazia
        #
        # "list(...)" cria uma cópia superficial (shallow copy) da lista,
        # impedindo que quem chamou altere diretamente a lista armazenada internamente.
        return list(self._data.get(session_id, []))

    def save(self, session_id: str, items: List[CartItem]) -> None:
        # Salva/substitui o carrinho associado ao session_id.
        #
        # A ideia aqui é simples: armazenamos o "estado inteiro" do carrinho.
        #
        # "list(items)" cria uma cópia superficial, evitando que o chamador
        # mantenha uma referência direta à lista interna do store.
        #
        # Observação didática:
        # - isso não clona profundamente cada CartItem, mas como CartItem é um objeto
        #   simples e a nossa lógica trabalha com a lista como unidade, esse nível já resolve
        #   o problema mais comum (vazamento de referência da lista).
        self._data[session_id] = list(items)

    def delete(self, session_id: str) -> None:
        # Remove o carrinho associado ao session_id.
        #
        # pop(..., None) torna a operação idempotente:
        # - se a chave não existir, não dá erro
        # Isso é importante para storages reais também (Redis, etc.).
        self._data.pop(session_id, None)
