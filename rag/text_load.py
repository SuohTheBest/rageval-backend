import json
import os
import sys

sys.path.append("./")

import logging
from sqlalchemy.exc import SQLAlchemyError
from models.Text import RAGText
from models.database import SessionLocal

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_json_file(file_path):
    """读取JSON文件并返回解析后的数据"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        logger.info(f"成功读取JSON文件: {file_path}")
        return data
    except Exception as e:
        logger.error(f"读取JSON文件失败: {str(e)}")
        return None


def convert_to_text_list(data):
    """
    将JSON数据转换为文本列表
    格式: "{item}\n---\n{title}:{str(content)}"
    """
    text_list = []

    for item, content_dict in data.items():
        for title, content in content_dict.items():
            # 将内容转换为字符串，无论是列表、字典还是其他类型
            text = f"{item}\n---\n{title}:{str(content)}"
            text_list.append(text)

    return text_list


def insert_texts_to_db(text_list):
    """将文本列表插入到数据库"""
    session = SessionLocal()
    try:
        count = 0
        for text in text_list:
            rag_text = RAGText(text=text)
            session.add(rag_text)
            count += 1

            # 每100条记录提交一次，避免事务过大
            if count % 100 == 0:
                session.commit()
                logger.info(f"已插入 {count} 条记录")

        # 提交剩余的记录
        session.commit()
        logger.info(f"成功插入总计 {count} 条记录到数据库")
        return count
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"插入数据库失败: {str(e)}")
        return 0
    finally:
        session.close()


def load_texts_from_json(json_path):
    """从JSON文件加载文本并插入数据库"""
    # 检查文件是否存在
    if not os.path.exists(json_path):
        logger.error(f"文件不存在: {json_path}")
        return False

    # 读取JSON文件
    data = read_json_file(json_path)
    if not data:
        return False

    # 转换为文本列表
    text_list = convert_to_text_list(data)
    logger.info(f"从JSON文件生成了 {len(text_list)} 条文本记录")

    # 插入数据库
    inserted_count = insert_texts_to_db(text_list)
    return inserted_count > 0


def main(json_path=None):
    """主函数，处理命令行参数"""
    if not json_path:
        json_path = "./data/result_weapons.json"  # 默认路径

    success = load_texts_from_json(json_path)
    if success:
        logger.info("数据加载完成")
    else:
        logger.error("数据加载失败")


if __name__ == "__main__":
    import sys

    # 允许通过命令行参数指定JSON文件路径
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(json_path)
