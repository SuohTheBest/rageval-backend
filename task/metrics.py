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

# rag
import pandas as pd
import os
from ragas import SingleTurnSample, EvaluationDataset
from ragas.metrics import BleuScore
from ragas.llms import LangchainLLMWrapper

# 原本的导入
# from task.utils import get_upload_filepath, get_task_from_id, get_download_filepath, remove_task
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from ragas.metrics import LLMContextRecall, Faithfulness, FactualCorrectness
from ragas import evaluate

def set_environment():
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    return evaluator_llm


def process_LLMContextPrecisionWithoutReference(user_inputs, responses, retrieved_contexts, df):
    dataset = []
    for user_input, response, retrieved_context in zip(user_inputs, responses, retrieved_contexts):
        dataset.append(
            SingleTurnSample(user_input=user_input, response=response,
                             retrieved_contexts=retrieved_context)
        )
    dataset = EvaluationDataset(dataset)
    evaluator_llm = set_environment()
    result = evaluate(dataset=dataset, metrics=[LLMContextPrecisionWithoutReference()
                                                ], llm=evaluator_llm)
    # result = result.to_pandas().to_csv()
    # 将 result 转换为 DataFrame，并获取最后一列
    result_df = result.to_pandas()
    last_column = result_df.iloc[:, -1]  # 获取最后一列
    # 将最后一列添加到原 df
    df['LLMContextPrecisionWithoutReference'] = last_column
    t = 0


def process_rag(task: Task):
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    from task.utils import get_upload_filepath

    # 这里回头当做做表用的ids，到时候需要解包
    input_ids = []
    input_ids.append(task.input_id)
    # 这里要处理的肯定是最后一个文件
    file = get_upload_filepath(input_ids[-1])
    user_input = []
    response = []
    reference = []
    retrieved_contexts = [[]]
    reference_contexts = [[]]
    df = pd.read_csv(file)
    user_input = df.get(
        "user_input", pd.Series([])
    ).tolist()  # 如果 'a' 不存在，返回空列表
    response = df.get("response", pd.Series([])).tolist()  # 如果 'a' 不存在，返回空列表
    reference = df.get(
        "reference", pd.Series([])
    ).tolist()  # 如果 'a' 不存在，返回空列表
    # retrieved_contexts = df.get('retrieved_contexts', pd.Series([[]])).tolist()
    # reference_contexts = df.get('reference_contexts', pd.Series([[]])).tolist()
    retrieved_contexts = [
        ast.literal_eval(item) if isinstance(item, str) else item
        for item in df.get("retrieved_contexts", pd.Series([[]])).tolist()
    ]
    reference_contexts = [
        ast.literal_eval(item) if isinstance(item, str) else item
        for item in df.get("reference_contexts", pd.Series([[]])).tolist()
    ]
    methods = []
    methods.append(task.method)
    for method in methods:
        if method == "method1":
            process_LLMContextPrecisionWithoutReference(
                user_input, response, retrieved_contexts, df
            )
    df.to_csv(f"{task.id}_output.csv", index=False)

