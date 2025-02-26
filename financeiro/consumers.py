import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificacaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"message": "Conexão WebSocket estabelecida"}))

    async def disconnect(self, close_code):
        print("WebSocket desconectado")

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({"message": f"Recebido: {data}"}))
