from django.db import transaction
from django.utils import timezone

from .models import Pedido, VariacaoProduto


class EstoqueInsuficiente(Exception):
    pass


@transaction.atomic
def alterar_status(pedido, novo_status):
    """Muda o status do pedido mantendo o estoque coerente.

    Confirmar baixa o estoque; voltar para aguardando ou cancelar devolve o
    que tinha sido baixado. Levanta EstoqueInsuficiente se não houver peças.
    """
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    deve_baixar = novo_status == Pedido.CONFIRMADO

    if deve_baixar != pedido.estoque_baixado:
        itens = list(pedido.itens.filter(produto__isnull=False))
        variacoes = {
            (v.produto_id, v.tamanho): v
            for v in VariacaoProduto.objects.select_for_update().filter(
                produto__in=[i.produto_id for i in itens]
            )
        }
        faltando = []
        for item in itens:
            variacao = variacoes.get((item.produto_id, item.tamanho))
            if deve_baixar:
                if variacao is None or variacao.estoque < item.quantidade:
                    faltando.append(
                        f'{item.nome} ({item.tamanho}): pedido {item.quantidade}, '
                        f'disponível {variacao.estoque if variacao else 0}'
                    )
                    continue
                variacao.estoque -= item.quantidade
            elif variacao is not None:
                variacao.estoque += item.quantidade
        if faltando:
            raise EstoqueInsuficiente('; '.join(faltando))
        VariacaoProduto.objects.bulk_update(variacoes.values(), ['estoque'])
        pedido.estoque_baixado = deve_baixar

    if novo_status == Pedido.CONFIRMADO and pedido.status != Pedido.CONFIRMADO:
        pedido.confirmado_em = timezone.now()
    elif novo_status != Pedido.CONFIRMADO:
        pedido.confirmado_em = None
    pedido.status = novo_status
    pedido.save(update_fields=['status', 'estoque_baixado', 'confirmado_em', 'atualizado_em'])
    return pedido
