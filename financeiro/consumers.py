from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Adiciona o cliente a um grupo de notificações
        await self.channel_layer.group_add("notifications", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove o cliente do grupo de notificações
        await self.channel_layer.group_discard("notifications", self.channel_name)

    async def send_notification(self, event):
        # Envia a mensagem para o cliente
        message = event['message']
        await self.send(text_data=json.dumps(message))