from fastapi import WebSocket, WebSocketDisconnect
import json
from collections import OrderedDict
import time


class ConnectionManager:
    def __init__(self, max_connections: int = 500):
        self.active_connections = {}  # Dict[str, WebSocket]
        self.connection_times = OrderedDict()  # OrderedDict[str, float]
        self.max_connections = max_connections

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

        # 添加新连接
        self.active_connections[client_id] = websocket
        self.connection_times[client_id] = time.time()

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_times[client_id]

    async def send(self, message: str, client_id: str):
        if client_id in self.active_connections:
            self.connection_times.move_to_end(client_id)
            self.connection_times[client_id] = time.time()

            try:
                await self.active_connections[client_id].send_text(message)
            except:
                # 如果发送失败，断开连接
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        for client_id in self.active_connections.keys():
            await self.send(message, client_id)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # 解析接收到的JSON数据
                data = json.loads(data)  # {type:"", content:""}
                type = data["type"]  # message, file, picture,
                content = data["content"]
                if type == "message":
                    response = {
                        "type": "message",
                        "content": {
                            "type": "assistant",
                            "content": f"收到消息: {data}"
                        }
                    }
                    await manager.send(
                        json.dumps(response),
                        client_id
                    )

            except json.JSONDecodeError:
                await manager.send(
                    json.dumps({
                        "type": "error",
                        "content": "无效的JSON格式"
                    }),
                    client_id
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
