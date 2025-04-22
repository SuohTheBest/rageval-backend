import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

sys.path.append("./")

from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
import os
from models.Text import RAGText
from models.database import SessionLocal
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 设置Chroma存储路径
CHROMA_PATH = "./data/chroma_db"

# 最大并发数
MAX_WORKERS = 64


def process_single_record(text_splitter, vectorstore, record):
    """处理单条文本记录的嵌入任务"""
    try:
        # 文本切分
        docs = text_splitter.create_documents(
            [record.text], metadatas=[{"source": f"text_{record.id}"}]
        )

        if not docs:
            logger.warning(f"文本ID {record.id} 切分后为空，跳过")
            return None

        # 添加到向量存储（包含自动嵌入）
        vectorstore.add_documents(docs)
        logger.info(f"成功处理文本ID: {record.id}, 生成了 {len(docs)} 个文档块")
        return record.id

    except Exception as e:
        logger.error(f"处理文本ID {record.id} 时出错: {str(e)}")
        return None


def process_database_to_chroma():
    """从数据库读取文本，并发进行切分、嵌入，并存储到Chroma"""
    start_time = time.time()
    # 初始化嵌入模型
    embeddings = OpenAIEmbeddings(
        base_url="https://api.bianxie.ai/v1",
        api_key="sk-6KauMKZj30SWwYYybrW1TYyfizVAyzOAYG5A5xw7JYy8oJkZ",
    )

    # 初始化文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100, length_function=len
    )

    # 初始化Chroma向量存储
    if os.path.exists(CHROMA_PATH):
        logger.info(f"加载现有Chroma数据库从 {CHROMA_PATH}")
        vectorstore = Chroma(
            persist_directory=CHROMA_PATH, embedding_function=embeddings
        )
    else:
        logger.info(f"创建新的Chroma数据库于 {CHROMA_PATH}")
        vectorstore = Chroma(
            persist_directory=CHROMA_PATH, embedding_function=embeddings
        )

    # 从数据库分批读取数据
    batch_size = 128
    db = SessionLocal()

    try:
        # 获取总记录数
        total_count = db.query(RAGText).count()
        logger.info(f"数据库中共有 {total_count} 条记录")
        processed_count = 0

        # 创建线程池
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 批量处理
            for offset in range(0, total_count, batch_size):
                logger.info(
                    f"处理批次: {offset//batch_size + 1}/{(total_count-1)//batch_size + 1}"
                )

                # 获取一批文本
                batch = db.query(RAGText).offset(offset).limit(batch_size).all()

                # 并发提交任务
                futures = []
                for record in batch:
                    future = executor.submit(
                        process_single_record, text_splitter, vectorstore, record
                    )
                    futures.append(future)

                # 等待所有任务完成
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        processed_count += 1

                # 每批次保存一次
                vectorstore.persist()
                logger.info(
                    f"批次 {offset//batch_size + 1} 已保存，当前已处理 {processed_count} 条记录"
                )

    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
    finally:
        db.close()
        # 最后保存一次以确保所有数据都持久化
        vectorstore.persist()
        elapsed_time = time.time() - start_time
        logger.info(
            f"处理完成，所有嵌入已保存，共处理 {processed_count} 条记录，耗时 {elapsed_time:.2f} 秒"
        )


if __name__ == "__main__":
    process_database_to_chroma()
