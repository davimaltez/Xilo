from django.contrib import admin, messages
from django.db.models import Count, F, Sum
from django.utils.html import format_html_join
from .models import (
    Categoria,
    Colecao,
    Produto,
    ImagemProduto,
    VariacaoProduto,
    Pedido,
    ItemPedido,
    Venda,
)
from .pedidos import EstoqueInsuficiente, alterar_status


admin.site.site_header = 'VEREDAS — Administração'
admin.site.site_title = 'VEREDAS'
admin.site.index_title = 'Painel da Loja'


class CamposAdminMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if field is not None:
            labels = {
                'descricao': 'Descrição',
                'preco': 'Preço (R$)',
                'colecao': 'Coleção',
                'slug': 'Identificador do endereço',
                'estoque': 'Quantidade disponível',
            }
            field.label = labels.get(db_field.name, field.label)
            if db_field.name == 'slug':
                field.help_text = 'Preenchido a partir do nome. Deve ser único.'
        return field


@admin.register(Categoria)
class CategoriaAdmin(CamposAdminMixin, admin.ModelAdmin):

    list_display = (
        'nome',
        'slug',
    )

    prepopulated_fields = {
        'slug': ('nome',)
    }


@admin.register(Colecao)
class ColecaoAdmin(CamposAdminMixin, admin.ModelAdmin):

    list_display = (
        'nome',
        'slug',
        'ordem',
    )

    fields = ('nome', 'slug', 'descricao', 'imagem', 'ordem')
    ordering = ('ordem', 'id')

    prepopulated_fields = {
        'slug': ('nome',)
    }

class ImagemProdutoInline(CamposAdminMixin, admin.TabularInline):

    model = ImagemProduto
    ordering = ('ordem', 'id')
    verbose_name = 'imagem'
    verbose_name_plural = 'Imagens dos produtos'
    extra = 1
    fields = (
        'imagem',
        'ordem',
    )


class VariacaoProdutoInline(CamposAdminMixin, admin.TabularInline):

    model = VariacaoProduto
    verbose_name = 'tamanho'
    verbose_name_plural = 'Estoque e tamanhos'
    extra = 1
    fields = (
        'tamanho',
        'estoque',
    )

@admin.register(Produto)
class ProdutoAdmin(CamposAdminMixin, admin.ModelAdmin):

    list_display = (
        'nome',
        'preco',
        'categoria',
        'colecao',
        'ativo',
        'destaque',
        'ordem',
    )

    list_editable = ('preco', 'ativo', 'destaque', 'ordem')
    list_select_related = ('categoria', 'colecao')
    ordering = ('-destaque', 'ordem', 'id')

    fieldsets = (
        ('Informações principais', {
            'fields': ('nome', 'descricao', 'preco'),
        }),
        ('Organização da loja', {
            'fields': ('categoria', 'colecao', 'ativo', 'destaque', 'ordem'),
            'description': 'Ativo exibe o produto na loja. Destaque coloca o produto antes dos demais.',
        }),
        ('Endereço do produto', {
            'fields': ('slug',),
            'classes': ('collapse',),
        }),
    )

    list_filter = (
        'categoria',
        'colecao',
        'ativo',
        'destaque',
    )

    search_fields = (
        'nome',
        'descricao',
    )

    prepopulated_fields = {
        'slug': ('nome',)
    }

    inlines = [
        ImagemProdutoInline,
        VariacaoProdutoInline,
    ]


class ItemPedidoInline(admin.TabularInline):

    model = ItemPedido
    verbose_name = 'item'
    verbose_name_plural = 'Itens do pedido'
    extra = 0
    can_delete = False
    fields = ('nome', 'tamanho', 'quantidade', 'preco_unitario', 'subtotal')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Subtotal (R$)')
    def subtotal(self, item):
        return item.subtotal


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'criado_em', 'resumo', 'total', 'status')
    list_filter = ('status', 'criado_em')
    date_hierarchy = 'criado_em'
    search_fields = ('id', 'itens__nome', 'observacoes')
    fields = ('status', 'total', 'criado_em', 'observacoes')
    readonly_fields = ('total', 'criado_em')
    inlines = [ItemPedidoInline]
    actions = ['confirmar', 'cancelar']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('itens')

    def has_add_permission(self, request):
        return False

    @admin.display(description='Itens')
    def resumo(self, pedido):
        return format_html_join(
            ', ', '{}x {} ({})',
            ((i.quantidade, i.nome, i.tamanho) for i in pedido.itens.all()),
        )

    def save_model(self, request, obj, form, change):
        novo_status = obj.status
        if change and 'status' in form.changed_data:
            obj.status = form.initial['status']
        super().save_model(request, obj, form, change)
        if obj.status != novo_status:
            try:
                alterar_status(obj, novo_status)
            except EstoqueInsuficiente as erro:
                self.message_user(
                    request,
                    f'{obj} não foi confirmado, falta estoque: {erro}',
                    messages.ERROR,
                )
            else:
                obj.status = novo_status

    def _aplicar(self, request, queryset, novo_status, rotulo):
        feitos = 0
        for pedido in queryset:
            if pedido.status == novo_status:
                continue
            try:
                alterar_status(pedido, novo_status)
                feitos += 1
            except EstoqueInsuficiente as erro:
                self.message_user(request, f'{pedido} não foi {rotulo}, falta estoque: {erro}', messages.ERROR)
        if feitos:
            self.message_user(request, f'{feitos} pedido(s) {rotulo}(s).', messages.SUCCESS)

    @admin.action(description='Confirmar pedidos selecionados (baixa o estoque)')
    def confirmar(self, request, queryset):
        self._aplicar(request, queryset, Pedido.CONFIRMADO, 'confirmado')

    @admin.action(description='Cancelar pedidos selecionados (devolve o estoque, se já baixado)')
    def cancelar(self, request, queryset):
        self._aplicar(request, queryset, Pedido.CANCELADO, 'cancelado')


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    """Relatório somente leitura dos pedidos confirmados."""

    change_list_template = 'admin/loja/venda/change_list.html'
    list_display = ('__str__', 'confirmado_em', 'resumo', 'total')
    date_hierarchy = 'confirmado_em'
    fields = ('total', 'criado_em', 'confirmado_em', 'observacoes')
    inlines = [ItemPedidoInline]
    list_filter = ('confirmado_em', 'itens__produto__colecao', 'itens__produto__categoria')
    search_fields = ('id', 'itens__nome', 'observacoes')
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).filter(status=Pedido.CONFIRMADO).prefetch_related('itens')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    resumo = PedidoAdmin.resumo

    def changelist_view(self, request, extra_context=None):
        resposta = super().changelist_view(request, extra_context)
        cl = getattr(resposta, 'context_data', {}).get('cl')
        if cl is None:
            return resposta

        vendas = Pedido.objects.filter(pk__in=cl.queryset.values('pk'))
        totais = vendas.aggregate(faturamento=Sum('total'), quantidade=Count('pk'))
        itens = ItemPedido.objects.filter(pedido__in=vendas)
        faturamento = totais['faturamento'] or 0
        resposta.context_data['resumo_vendas'] = {
            'faturamento': faturamento,
            'quantidade': totais['quantidade'],
            'ticket_medio': faturamento / totais['quantidade'] if totais['quantidade'] else 0,
            'pecas': itens.aggregate(soma=Sum('quantidade'))['soma'] or 0,
            'mais_vendidos': itens.values('nome').annotate(
                pecas=Sum('quantidade'),
                valor=Sum(F('quantidade') * F('preco_unitario')),
            ).order_by('-pecas', '-valor')[:5],
        }
        return resposta
