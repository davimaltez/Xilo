import json

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .models import Produto, VariacaoProduto, ImagemProduto, Colecao, Pedido, ItemPedido


@ensure_csrf_cookie
def home(request):

    produtos = Produto.objects.filter(
        ativo=True
    ).prefetch_related(
        Prefetch('imagens', queryset=ImagemProduto.objects.order_by('ordem', 'id')),
        'variacoes'
    ).select_related(
        'categoria',
        'colecao'
    ).order_by('ordem', 'id')

    produto_hero = produtos.filter(destaque=True).first() or produtos.first()
    imagens_hero = list(produto_hero.imagens.all()) if produto_hero else []
    imagem_hero = imagens_hero[0] if imagens_hero else None

    return render(
        request,
        'loja/index.html',
        {
            'produtos': produtos,
            'colecoes': Colecao.objects.order_by('ordem', 'id'),
            'produto_hero': produto_hero,
            'imagem_hero': imagem_hero,
            'imagens_hero': imagens_hero,
            'whatsapp_numero': settings.WHATSAPP_NUMERO,
        }
    )

@require_POST
def criar_pedido(request):
    """Valida o estoque da sacola e registra o pedido como aguardando confirmação."""
    try:
        dados = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'valido': False, 'erro': 'JSON inválido.'}, status=400)

    itens = dados.get('itens') if isinstance(dados, dict) else None
    if not isinstance(itens, list) or not itens:
        return JsonResponse({'valido': False, 'erro': 'Carrinho vazio ou inválido.'}, status=400)

    quantidades = {}
    tamanhos = dict(VariacaoProduto.TAMANHOS)
    for item in itens:
        if not isinstance(item, dict):
            return JsonResponse({'valido': False, 'erro': 'Item inválido.'}, status=400)

        produto_id = item.get('id')
        tamanho = item.get('size')
        quantidade = item.get('quantity')
        if (
            type(produto_id) is not int or not 0 < produto_id <= 9223372036854775807
            or not isinstance(tamanho, str) or tamanho not in tamanhos
            or type(quantidade) is not int or quantidade <= 0
        ):
            return JsonResponse({'valido': False, 'erro': 'Produto, tamanho ou quantidade inválidos.'}, status=400)

        chave = (produto_id, tamanho)
        quantidades[chave] = quantidades.get(chave, 0) + quantidade

    produtos = {
        produto.pk: produto
        for produto in Produto.objects.filter(
            pk__in={produto_id for produto_id, _ in quantidades}
        ).prefetch_related('variacoes')
    }
    estoques = {
        (produto.pk, variacao.tamanho): variacao.estoque
        for produto in produtos.values() if produto.ativo
        for variacao in produto.variacoes.all()
    }
    erros = []
    for (produto_id, tamanho), quantidade in quantidades.items():
        produto = produtos.get(produto_id)
        disponivel = estoques.get((produto_id, tamanho), 0)
        if quantidade > disponivel:
            erros.append({
                'produto_id': produto_id,
                'produto': produto.nome if produto else 'Produto indisponível',
                'tamanho': tamanho,
                'quantidade_solicitada': quantidade,
                'quantidade_disponivel': disponivel,
            })

    if erros:
        return JsonResponse({'valido': False, 'erros': erros})

    with transaction.atomic():
        pedido = Pedido.objects.create(
            total=sum(produtos[pid].preco * qtd for (pid, _), qtd in quantidades.items())
        )
        ItemPedido.objects.bulk_create([
            ItemPedido(
                pedido=pedido,
                produto=produtos[pid],
                nome=produtos[pid].nome,
                tamanho=tamanho,
                quantidade=qtd,
                preco_unitario=produtos[pid].preco,
            )
            for (pid, tamanho), qtd in quantidades.items()
        ])

    return JsonResponse({'valido': True, 'pedido': pedido.pk})
