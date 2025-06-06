from fastapi import WebSocket
import json
from collections import OrderedDict
import time


class ConnectionManager:
    def __init__(self, max_connections: int = 500):
        self.active_connections = {}  # Dict[str, WebSocket]
        self.user_config = {}
        self.connection_times = OrderedDict()  # OrderedDict[str, float]
        self.max_connections = max_connections

    def set_config(self, client_id: str, model: str, temperature: float):
        self.user_config[client_id] = {'model': model, 'temperature': temperature}

    def get_config(self, client_id: str) -> dict | None:
        if client_id in self.user_config:
            return self.user_config[client_id]
        else:
            return None

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()

        # 如果用户已有连接，先断开旧连接
        if client_id in self.active_connections:
            old_websocket = self.active_connections[client_id]
            try:
                await old_websocket.close()
            except:
                pass
            del self.active_connections[client_id]
            del self.connection_times[client_id]

        if client_id in self.user_config:
            del self.user_config[client_id]

        # 如果达到最大连接数，移除最旧的连接
        if len(self.active_connections) >= self.max_connections:
            oldest_client = next(iter(self.connection_times))
            oldest_websocket = self.active_connections[oldest_client]
            try:
                await oldest_websocket.close()
            except:
                pass
            del self.active_connections[oldest_client]
            del self.connection_times[oldest_client]

        if client_id in self.user_config:
            del self.user_config[client_id]

        # 添加新连接
        self.active_connections[client_id] = websocket
        self.connection_times[client_id] = time.time()

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_times[client_id]

        if client_id in self.user_config:
            del self.user_config[client_id]

    async def send(self, message: str, client_id: str):
        if client_id in self.active_connections:
            self.connection_times.move_to_end(client_id)
            self.connection_times[client_id] = time.time()
            try:
                await self.active_connections[client_id].send_text(message)
            except:
                # 如果发送失败，断开连接
                self.disconnect(client_id)

    async def send_stream(self, client_id: str, stream_type: str, content: str):
        """发送流式消息"""
        if client_id in self.active_connections:
            self.connection_times.move_to_end(client_id)
            self.connection_times[client_id] = time.time()
            try:
                await self.active_connections[client_id].send_text(
                    json.dumps(
                        {
                            "type": "stream",
                            "content": {
                                "stream_type": stream_type,  # start, content, end
                                "content": content,
                            },
                        }
                    )
                )
            except:
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        for client_id in self.active_connections.keys():
            await self.send(message, client_id)


manager = ConnectionManager()
