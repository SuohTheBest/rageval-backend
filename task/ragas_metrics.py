from ragas import evaluate
import os
from ragas import SingleTurnSample, EvaluationDataset
from ragas.metrics import BleuScore
from ragas.llms import LangchainLLMWrapper
# 原本的导入
# from task.utils import get_upload_filepath, get_task_from_id, get_download_filepath, remove_task
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from ragas.metrics import *


def set_environment():
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    return evaluator_llm


def evaluate_and_store(dataset, metric, llm, df, name):
    result = evaluate(dataset=dataset, metrics=[metric], llm=llm)
    result_df = result.to_pandas()
    last_column = result_df.iloc[:, -1]  # 获取最后一列
    df[name] = last_column


def process_LLMContextPrecisionWithoutReference(user_inputs, responses, retrieved_contexts, df):
    dataset = []
    for user_input, response, retrieved_context in zip(user_inputs, responses, retrieved_contexts):
        dataset.append(
            SingleTurnSample(user_input=user_input, response=response,
                             retrieved_contexts=retrieved_context)
        )
    dataset = EvaluationDataset(dataset)
    evaluator_llm = set_environment()
    # result = evaluate(dataset=dataset, metrics=[LLMContextPrecisionWithoutReference()
    #                                             ], llm=evaluator_llm)
    # # 将 result 转换为 DataFrame，并获取最后一列
    # result_df = result.to_pandas()
    # last_column = result_df.iloc[:, -1]  # 获取最后一列
    # # 将最后一列添加到原 df
    # df['LLMContextPrecisionWithoutReference'] = last_column
    evaluate_and_store(
        dataset, LLMContextPrecisionWithoutReference(), evaluator_llm, df, 'LLMContextPrecisionWithoutReference')
