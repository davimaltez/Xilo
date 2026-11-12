from django.db import models


class Categoria(models.Model):

    nome = models.CharField(max_length=100)

    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.nome


class Colecao(models.Model):

    nome = models.CharField(max_length=100)

    slug = models.SlugField(unique=True)

    imagem = models.ImageField(
        'Imagem da coleção',
        upload_to='colecoes/',
        blank=True,
        null=True,
    )

    descricao = models.TextField('Descrição', blank=True)

    ordem = models.PositiveIntegerField(
        default=0,
        help_text='Menores números aparecem primeiro.',
    )

    def __str__(self):
        return self.nome


class Produto(models.Model):

    nome = models.CharField(max_length=200)

    slug = models.SlugField(unique=True)

    descricao = models.TextField(blank=True)

    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos'
    )

    colecao = models.ForeignKey(
        Colecao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos'
    )

    ativo = models.BooleanField(default=True)

    destaque = models.BooleanField(default=False)

    ordem = models.PositiveIntegerField(
        default=0,
        help_text='Menores números aparecem primeiro, dentro de cada grupo de destaque.',
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


class ImagemProduto(models.Model):

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='imagens'
    )

    imagem = models.ImageField(
        upload_to='produtos/'
    )

    ordem = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Imagem de {self.produto.nome}"


class VariacaoProduto(models.Model):

    TAMANHOS = [
        ('P', 'P'),
        ('M', 'M'),
        ('G', 'G'),
        ('GG', 'GG'),
    ]

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='variacoes'
    )

    tamanho = models.CharField(
        max_length=2,
        choices=TAMANHOS
    )

    estoque = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.produto.nome} - {self.tamanho}"

class Pedido(models.Model):

    AGUARDANDO = 'aguardando'
    CONFIRMADO = 'confirmado'
    CANCELADO = 'cancelado'
    STATUS = [
        (AGUARDANDO, 'Aguardando confirmação'),
        (CONFIRMADO, 'Confirmado'),
        (CANCELADO, 'Cancelado'),
    ]

    status = models.CharField(max_length=20, choices=STATUS, default=AGUARDANDO)

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Anotações internas: nome da cliente, frete combinado, forma de pagamento etc.',
    )

    estoque_baixado = models.BooleanField(default=False, editable=False)

    criado_em = models.DateTimeField('Recebido em', auto_now_add=True)

    confirmado_em = models.DateTimeField('Vendido em', null=True, blank=True, editable=False)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-criado_em',)

    def __str__(self):
        return f'Pedido #{self.pk}'


class Venda(Pedido):
    """Pedidos confirmados, exibidos no admin como relatório de vendas."""

    class Meta:
        proxy = True
        ordering = ('-confirmado_em',)
        verbose_name = 'venda'
        verbose_name_plural = 'vendas'


class ItemPedido(models.Model):

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')

    produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_pedido',
    )

    nome = models.CharField('Produto', max_length=200)

    tamanho = models.CharField(max_length=2, choices=VariacaoProduto.TAMANHOS)

    quantidade = models.PositiveIntegerField()

    preco_unitario = models.DecimalField('Preço unitário (R$)', max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.quantidade}x {self.nome} ({self.tamanho})'

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
