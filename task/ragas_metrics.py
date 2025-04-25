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
from task.utils import get_upload_filepath

import ast
from models.Task import Task


def process_rag(task: Task):
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)

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
    user_input = df.get('user_input', pd.Series([])
                        ).tolist()  # 如果 'a' 不存在，返回空列表
    response = df.get('response', pd.Series([])).tolist()  # 如果 'a' 不存在，返回空列表
    reference = df.get('reference', pd.Series([])).tolist()  # 如果 'a' 不存在，返回空列表
    # retrieved_contexts = df.get('retrieved_contexts', pd.Series([[]])).tolist()
    # reference_contexts = df.get('reference_contexts', pd.Series([[]])).tolist()
    retrieved_contexts = [ast.literal_eval(item) if isinstance(
        item, str) else item for item in df.get('retrieved_contexts', pd.Series([[]])).tolist()]
    reference_contexts = [ast.literal_eval(item) if isinstance(
        item, str) else item for item in df.get('reference_contexts', pd.Series([[]])).tolist()]
    methods = []
    methods.append(task.method)
    for method in methods:
        if method == "method1":
            process_LLMContextPrecisionWithoutReference(
                user_input, response, retrieved_contexts, df)
    df.to_csv(f'{task.id}_output.csv', index=False)


def set_environment():
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    return evaluator_llm


def generate_dataset(fields, context_type='user_input'):
    """
    通用的函数来生成 dataset，根据传入的字段动态生成 `SingleTurnSample`
    """
    dataset = []
    for field_set in zip(*fields):  # 这将自动处理多个字段的情况
        sample_data = {}
        if 'user_input' in fields:
            sample_data['user_input'] = field_set[fields.index('user_input')]
        if 'response' in fields:
            sample_data['response'] = field_set[fields.index('response')]
        if 'reference' in fields:
            sample_data['reference'] = field_set[fields.index('reference')]
        if 'retrieved_contexts' in fields:
            sample_data['retrieved_contexts'] = field_set[fields.index(
                'retrieved_contexts')]
        if 'reference_contexts' in fields:
            sample_data['reference_contexts'] = field_set[fields.index(
                'reference_contexts')]

        # 根据提供的字段动态构建 SingleTurnSample
        dataset.append(SingleTurnSample(**sample_data))

    return EvaluationDataset(dataset)


def evaluate_and_store(dataset, metric, llm, df, name):
    result = evaluate(dataset=dataset, metrics=[metric], llm=llm)
    result_df = result.to_pandas()
    last_column = result_df.iloc[:, -1]  # 获取最后一列
    df[name] = last_column


def process_LLMContextPrecisionWithoutReference(user_inputs, responses, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = generate_dataset(
        [user_inputs, responses, retrieved_contexts], fields)
    dataset = EvaluationDataset(dataset)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, LLMContextPrecisionWithoutReference(), evaluator_llm, df, 'LLMContextPrecisionWithoutReference')


def process_LLMContextPrecisionWithReference(user_inputs, references, retrieved_contexts, df):
    fields = ['user_input', 'reference', 'retrieved_contexts']
    dataset = generate_dataset(
        [user_inputs, references, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, LLMContextPrecisionWithReference(), evaluator_llm, df, 'LLMContextPrecisionWithReference')


def process_NonLLMContextPrecisionWithReference(retrieved_contexts, reference_contexts, df):
    fields = ['retrieved_contexts', 'reference_contexts']
    dataset = generate_dataset(
        [retrieved_contexts, reference_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, NonLLMContextPrecisionWithReference(), evaluator_llm, df, 'LLMContextPrecisionWithReference')


def process_LLMContextRecall(user_inputs, responses, references, retrieved_contexts, df):
    fields = ['user_input', 'response', 'reference', 'retrieved_contexts']
    dataset = generate_dataset(
        [user_inputs, responses, references, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, LLMContextRecall(), evaluator_llm, df, 'LLMContextRecall')


def process_NonLLMContextRecall(retrieved_contexts, reference_contexts, df):
    fields = ['retrieved_contexts', 'reference_contexts']
    dataset = generate_dataset(
        [retrieved_contexts, reference_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, NonLLMContextRecall(), evaluator_llm, df, 'NonLLMContextRecall')


def process_ContextEntityRecall(reference, retrieved_contexts, df):
    fields = ['reference', 'retrieved_contexts']
    dataset = [[reference, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ContextEntityRecall(), evaluator_llm, df, 'ContextEntityRecall')


def process_NoiseSensitivity(user_input, response, reference, retrieved_contexts, df):
    fields = ['user_input', 'response', 'reference', 'retrieved_contexts']
    dataset = [[user_input, response, reference, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, NoiseSensitivity(), evaluator_llm, df, 'NoiseSensitivity')


def process_ResponseRelevancy(user_input, response, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = [[user_input, response, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ResponseRelevancy(), evaluator_llm, df, 'ResponseRelevancy')


def process_Faithfulness(user_input, response, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = [[user_input, response, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, Faithfulness(), evaluator_llm, df, 'Faithfulness')


def process_FaithfulnesswithHHEM(user_input, response, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = [[user_input, response, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, FaithfulnesswithHHEM(), evaluator_llm, df, 'FaithfulnesswithHHEM')


def process_AnswerAccuracy(user_input, response, reference, df):
    fields = ['user_input', 'response', 'reference']
    dataset = [[user_input, response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, AnswerAccuracy(), evaluator_llm, df, 'AnswerAccuracy')


def process_ContextRelevance(user_input, retrieved_contexts, df):
    fields = ['user_input', 'retrieved_contexts']
    dataset = [[user_input, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ContextRelevance(), evaluator_llm, df, 'ContextRelevance')


def process_ResponseGroundedness(response, retrieved_contexts, df):
    fields = ['response', 'retrieved_contexts']
    dataset = [[response, retrieved_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ResponseGroundedness(), evaluator_llm, df, 'ResponseGroundedness')


def process_FactualCorrectness(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, FactualCorrectness(), evaluator_llm, df, 'FactualCorrectness')


def process_SemanticSimilarity(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, SemanticSimilarity(), evaluator_llm, df, 'SemanticSimilarity')


def process_NonLLMStringSimilarity(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, NonLLMStringSimilarity(), evaluator_llm, df, 'NonLLMStringSimilarity')


def process_BleuScore(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, BleuScore(), evaluator_llm, df, 'BleuScore')


def process_RougeScore(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, RougeScore(), evaluator_llm, df, 'RougeScore')


def process_ExactMatch(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ExactMatch(), evaluator_llm, df, 'ExactMatch')


def process_StringPresence(response, reference, df):
    fields = ['response', 'reference']
    dataset = [[response, reference], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, StringPresence(), evaluator_llm, df, 'StringPresence')


def process_SummarizationScore(response, reference_contexts, df):
    fields = ['response', 'reference_contexts']
    dataset = [[response, reference_contexts], fields]
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, SummarizationScore(), evaluator_llm, df, 'SummarizationScore')
