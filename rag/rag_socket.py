from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect
import json
from rag.application.assistant import create_assistant_service
from rag.utils.chat_session import (
    create_session,
    get_session,
    save_message_with_temp_file,
    save_assistant_message, MessageModel, FileOrPictureModel,
)
from rag.utils.socket_manager import manager

assistant = create_assistant_service()
temp_files: Dict[str, dict] = {}


async def rag_streaming_response(
        client_id: str, message: MessageModel, source: FileOrPictureModel
):
    """使用 assistant.process_request 处理并流式响应"""
    full_response_content = ""
    try:
        # 开始标记
        await manager.send_stream(client_id, "start", "")

        response_generator, retrieval_sources = await assistant.process_request(
            request=message, stream=True, extend_source=source, client_id=client_id
        )
        await manager.send_stream(client_id, "end_think", "")

        # 逐块处理流式内容
        async for chunk in response_generator:
            await manager.send_stream(client_id, "content", chunk)
            full_response_content += chunk

        if retrieval_sources and len(retrieval_sources) > 0:
            retrieval_arr = list(map(lambda r: {"title": r.title,
                                                "url": r.url,
                                                "snippet": r.snippet,
                                                "similarityScore": r.similarity_score},
                                     retrieval_sources))
            await manager.send_stream(client_id, "sources", retrieval_arr)
        # 保存助手消息
        save_assistant_message(
            session_id=message.session_id,
            content=full_response_content,
            retrieval=retrieval_sources,
        )

        # 结束标记
        await manager.send_stream(client_id, "end", '')

    except Exception as e:
        # 处理在 process_request 或流式处理中发生的错误
        error_message = f"Error processing request: {str(e)}"
        print(error_message)  # 记录错误到服务器日志
        try:
            # 尝试向客户端发送错误信息
            await manager.send_stream(client_id, "error", error_message)
            # 确保发送结束标记，即使有错误
            await manager.send_stream(client_id, "end", "")
        except Exception as send_error:
            # 如果发送错误信息也失败，则记录
            print(f"Failed to send error to client {client_id}: {str(send_error)}")
        # 根据错误类型，可能还需要断开连接或进行其他清理
        # self.disconnect(client_id) # 例如


async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # 解析接收到的JSON数据
                data = json.loads(data)  # {type:"", content:""}
                type = data["type"]  # message
                if type == "message":
                    # ChatMessage, 用户传输的包含type, content, session_id和额外的assistant_id
                    content = data["content"]
                    assistant_id = content["assistant_id"]
                    session_id = content["session_id"]  # 为None时需新建
                    temp_file_id = content.get("temp_file_id")  # 可选的临时文件ID
                    # 获取或创建会话
                    if session_id is None:
                        session = create_session(int(client_id), assistant_id)
                        session_id = session.id
                        # 发送session_id
                        response = {"type": "setSessionId", "content": session_id}
                        await manager.send(json.dumps(response), client_id)
                    else:
                        session = get_session(session_id)
                        if not session:
                            raise ValueError("Invalid session_id")
                    # 保存用户消息和关联的临时文件
                    message, file_or_picture_source = save_message_with_temp_file(
                        session_id=session_id,
                        role="user",
                        content=content["content"],
                        feature=content.get("feature"),
                        temp_file_id=temp_file_id,
                        temp_files=temp_files,
                    )
                    # 开始流式响应
                    await rag_streaming_response(
                        client_id, message, file_or_picture_source
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
