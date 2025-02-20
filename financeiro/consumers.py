import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Chamado quando o cliente WebSocket se conecta"""
        await self.accept()
        await self.channel_layer.group_add("notificacoes", self.channel_name)

    async def disconnect(self, close_code):
        """Chamado quando o cliente WebSocket se desconecta"""
        await self.channel_layer.group_discard("notificacoes", self.channel_name)

    async def receive(self, text_data):
        """Recebe mensagens do cliente WebSocket (opcional)"""
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({
            "message": data["message"]
        }))

    async def send_notification(self, event):
        """Envia notificações do servidor para o cliente"""
        await self.send(text_data=json.dumps({
            "message": event["message"]
        }))