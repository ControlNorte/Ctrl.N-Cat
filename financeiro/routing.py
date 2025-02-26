from django.urls import path
from .consumers import NotificacaoConsumer

websocket_urlpatterns = [
    path("ws/notificacao/", NotificacaoConsumer.as_asgi()),
]