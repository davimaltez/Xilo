from django.urls import path
from .views import home, criar_pedido


urlpatterns = [
    path('', home, name='home'),
    path('api/pedidos/', criar_pedido, name='criar_pedido'),
]