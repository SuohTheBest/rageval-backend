from fastapi import WebSocket, WebSocketDisconnect
import json
from collections import OrderedDict
import time
from rag.utils.session import create_session, get_session, save_message
import asyncio


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


async def test_streaming_response(client_id: str, session_id: int, content: str):
    """模拟流式响应"""
    words = content.split()
    full_response = "收到消息:" + content

    # 开始标记
    await manager.send_stream(client_id, "start", "")

    # 逐字发送
    for char in full_response:
        await manager.send_stream(client_id, "content", char)
        await asyncio.sleep(0.5)  # 模拟处理延迟

    # 结束标记
    await manager.send_stream(client_id, "end", full_response)

    save_message(session_id=session_id, type="assistant", content=full_response)


async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # 解析接收到的JSON数据
                data = json.loads(data)  # {type:"", content:""}
                type = data["type"]  # message, file, picture,
                if type == "message":
                    content = data[
                        "content"
                    ]  # ChatMessage, 用户传输的包含type, content, session_id和额外的assistant_id
                    assistant_id = content["assistant_id"]
                    session_id = content["session_id"]  # 为None时需新建

                    # 获取或创建会话
                    if session_id is None:
                        session = create_session(int(client_id), assistant_id)
                        session_id = session.id
                    else:
                        session = get_session(session_id)
                        if not session:
                            raise ValueError("Invalid session_id")

                    # 保存用户消息
                    save_message(
                        session_id=session_id, type="user", content=content["content"]
                    )
                    # 发送session_id
                    response = {"type": "setSessionId", "content": session_id}
                    await manager.send(json.dumps(response), client_id)
                    # 开始流式响应
                    await test_streaming_response(
                        client_id, session_id, content["content"]
                    )

            except json.JSONDecodeError:
                await manager.send(
                    json.dumps({"type": "error", "content": "无效的JSON格式"}),
                    client_id,
                )
            except ValueError as e:
                await manager.send(
                    json.dumps({"type": "error", "content": str(e)}), client_id
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
