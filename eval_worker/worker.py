import queue

MAX_SIZE = 100
# 准备使用生产者消费者模型🤩
waiting_list = queue.Queue(maxsize=MAX_SIZE)


async def add_task():
    global waiting_list
    if not waiting_list.full():
