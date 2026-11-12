import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import ItemPedido, Pedido, Produto, VariacaoProduto


class PedidoTests(TestCase):

    def setUp(self):
        self.produto = Produto.objects.create(nome='Camisa', slug='camisa', preco=Decimal('100.00'))
        self.variacao = VariacaoProduto.objects.create(produto=self.produto, tamanho='M', estoque=3)
        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'senha')

    def pedir(self, quantidade):
        return self.client.post(
            '/api/pedidos/',
            json.dumps({'itens': [{'id': self.produto.pk, 'size': 'M', 'quantity': quantidade}]}),
            content_type='application/json',
        ).json()

    def mudar_status(self, pedido, status):
        self.client.force_login(self.admin)
        return self.client.post('/admin/loja/pedido/', {
            'action': 'confirmar' if status == Pedido.CONFIRMADO else 'cancelar',
            '_selected_action': [pedido.pk],
        })

    def test_cria_pedido_aguardando_sem_baixar_estoque(self):
        resposta = self.pedir(2)
        pedido = Pedido.objects.get(pk=resposta['pedido'])
        self.assertEqual(pedido.status, Pedido.AGUARDANDO)
        self.assertEqual(pedido.total, Decimal('200.00'))
        self.assertEqual(ItemPedido.objects.get(pedido=pedido).quantidade, 2)
        self.variacao.refresh_from_db()
        self.assertEqual(self.variacao.estoque, 3)

    def test_recusa_sem_estoque(self):
        self.assertFalse(self.pedir(4)['valido'])
        self.assertFalse(Pedido.objects.exists())

    def test_confirmar_baixa_e_cancelar_devolve(self):
        pedido = Pedido.objects.get(pk=self.pedir(2)['pedido'])
        self.mudar_status(pedido, Pedido.CONFIRMADO)
        self.variacao.refresh_from_db()
        self.assertEqual(self.variacao.estoque, 1)
        self.mudar_status(pedido, Pedido.CANCELADO)
        self.variacao.refresh_from_db()
        self.assertEqual(self.variacao.estoque, 3)

    def test_nao_confirma_sem_estoque(self):
        pedido = Pedido.objects.get(pk=self.pedir(3)['pedido'])
        self.variacao.estoque = 1
        self.variacao.save()
        self.mudar_status(pedido, Pedido.CONFIRMADO)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.AGUARDANDO)

    def test_alterar_status_pelo_formulario(self):
        pedido = Pedido.objects.get(pk=self.pedir(1)['pedido'])
        self.client.force_login(self.admin)
        self.client.post(f'/admin/loja/pedido/{pedido.pk}/change/', {
            'status': Pedido.CONFIRMADO, 'observacoes': 'Frete R$ 20',
            'itens-TOTAL_FORMS': 1, 'itens-INITIAL_FORMS': 1, 'itens-MIN_NUM_FORMS': 0, 'itens-MAX_NUM_FORMS': 1000,
            'itens-0-id': pedido.itens.get().pk, 'itens-0-pedido': pedido.pk,
        })
        pedido.refresh_from_db()
        self.variacao.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.CONFIRMADO)
        self.assertEqual(pedido.observacoes, 'Frete R$ 20')
        self.assertEqual(self.variacao.estoque, 2)
        self.assertEqual(self.client.get('/admin/loja/pedido/').status_code, 200)
        self.assertEqual(self.client.get('/admin/loja/imagemproduto/').status_code, 404)

    def test_painel_mostra_pedidos_aguardando(self):
        pedido = Pedido.objects.get(pk=self.pedir(2)['pedido'])
        self.client.force_login(self.admin)
        html = self.client.get('/admin/').content.decode()
        self.assertIn('Pedidos aguardando confirmação', html)
        self.assertIn(f'/admin/loja/pedido/{pedido.pk}/change/', html)
        self.assertIn('2x Camisa (M)', html)
        self.assertNotIn('recent-actions-module', html)

    def test_relatorio_de_vendas(self):
        confirmado = Pedido.objects.get(pk=self.pedir(2)['pedido'])
        self.pedir(1)  # continua aguardando, não entra nas vendas
        self.mudar_status(confirmado, Pedido.CONFIRMADO)
        confirmado.refresh_from_db()
        self.assertIsNotNone(confirmado.confirmado_em)

        resposta = self.client.get('/admin/loja/venda/')
        self.assertEqual(resposta.status_code, 200)
        resumo = resposta.context['resumo_vendas']
        self.assertEqual(resumo['quantidade'], 1)
        self.assertEqual(resumo['faturamento'], Decimal('200.00'))
        self.assertEqual(resumo['pecas'], 2)
        self.assertEqual(list(resumo['mais_vendidos'])[0]['nome'], 'Camisa')
        self.assertEqual(self.client.get(f'/admin/loja/venda/{confirmado.pk}/change/').status_code, 200)

        self.mudar_status(confirmado, Pedido.CANCELADO)
        confirmado.refresh_from_db()
        self.assertIsNone(confirmado.confirmado_em)
        self.assertEqual(self.client.get('/admin/loja/venda/').context['resumo_vendas']['quantidade'], 0)
