from django import template
from django.db.models import Sum

from loja.models import Pedido

register = template.Library()


@register.simple_tag
def pedidos_aguardando(limite=8):
    pendentes = Pedido.objects.filter(status=Pedido.AGUARDANDO)
    return {
        'total': pendentes.count(),
        'valor': pendentes.aggregate(soma=Sum('total'))['soma'] or 0,
        'lista': pendentes.prefetch_related('itens')[:limite],
    }
