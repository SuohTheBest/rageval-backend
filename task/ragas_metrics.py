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
# from task.utils import get_upload_filepath

import ast
from models.Task import Task, RAGEvaluation


def process_rag(eval: RAGEvaluation):
    print("here is processing")
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    # llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    # evaluator_llm = LangchainLLMWrapper(llm)
    # 这里回头当做做表用的ids，到时候需要解包
    # input_ids = []
    # input_ids.append(eval.input_id)
    # 这里要处理的肯定是最后一个文件
    from task.utils import get_upload_filepath
    file = get_upload_filepath(eval.input_id)

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
    retrieved_contexts = [ast.literal_eval(item) if isinstance(
        item, str) else item for item in df.get('retrieved_contexts', pd.Series([[]])).tolist()]
    reference_contexts = [ast.literal_eval(item) if isinstance(
        item, str) else item for item in df.get('reference_contexts', pd.Series([[]])).tolist()]
    method = eval.method
    if method == "基于大模型的无参考上下文准确性":
        process_LLMContextPrecisionWithoutReference(
            user_input, response, retrieved_contexts, df)
    elif method == "基于大模型的有参考上下文准确性":
        process_LLMContextPrecisionWithReference(
            user_input, reference, retrieved_contexts, df)
    elif method == "有参考上下文准确性":
        process_NonLLMContextPrecisionWithReference(
            retrieved_contexts, reference_contexts, df)
    elif method == "基于大模型的上下文召回率":
        process_LLMContextRecall(
            user_input, response, reference, retrieved_contexts, df)
    elif method == "上下文召回率":
        process_NonLLMContextRecall(retrieved_contexts, reference_contexts, df)
    elif method == "上下文实体召回率":
        process_ContextEntityRecall(reference, retrieved_contexts, df)
    elif method == "噪声敏感度":
        process_NoiseSensitivity(user_input, response,
                                 reference, retrieved_contexts, df)
    elif method == "回答相关性":
        process_ResponseRelevancy(user_input, response, retrieved_contexts, df)
    elif method == "置信度":
        process_Faithfulness(user_input, response, retrieved_contexts, df)
    elif method == "带幻觉检测的置信度":
        process_FaithfulnesswithHHEM(
            user_input, response, retrieved_contexts, df)
    elif method == "回答准确率":
        process_AnswerAccuracy(user_input, response, reference, df)
    elif method == "上下文相关性":
        process_ContextRelevance(user_input, retrieved_contexts, df)
    elif method == "响应扎根性":
        process_ResponseGroundedness(response, retrieved_contexts, df)
    elif method == "事实准确性":
        process_FactualCorrectness(response, reference, df)
    elif method == "语义相似性":
        process_SemanticSimilarity(response, reference, df)
    elif method == "字符串相似度":
        process_NonLLMStringSimilarity(response, reference, df)
    elif method == "Bleu分数":
        process_BleuScore(response, reference, df)
    elif method == "Rouge分数":
        process_RougeScore(response, reference, df)
    elif method == "摘要得分":
        process_SummarizationScore(response, reference_contexts, df)

    file_path = f'downloads/{eval.task_id}_{eval.id}_{method}.csv'
    df.to_csv(file_path, index=False)
    file_size = os.path.getsize(file_path)
    last_column = df.iloc[:, -1]
    average = last_column.mean()
    result = average
    from task.utils import get_new_output_id
    output_id = get_new_output_id(
        eval.task_id, f'downloads/{eval.task_id}_{eval.id}_{method}.csv', file_size)
    eval.output_id = output_id
    result = int(output_id)
    return result


def set_environment():
    # os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    # os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    return evaluator_llm


def generate_dataset(fields_data, field_names):
    """
    通用的函数来生成 dataset，根据传入的字段动态生成 `SingleTurnSample`
    """
    dataset = []
    for field_set in zip(*fields_data):  # 这将自动处理多个字段的情况
        sample_data = {}

        # 遍历每个字段名，按顺序将数据添加到 sample_data 中
        for i, field_name in enumerate(field_names):
            sample_data[field_name] = field_set[i]  # 根据字段名动态存入对应数据

        # 使用构造函数来创建 SingleTurnSample
        dataset.append(SingleTurnSample(**sample_data))
    print("dataset:")
    print(dataset)
    return EvaluationDataset(dataset)


def evaluate_and_store(dataset, metric, llm, df, name):
    result = evaluate(dataset=dataset, metrics=[metric], llm=llm)
    result_df = result.to_pandas()
    last_column = result_df.iloc[:, -1]  # 获取最后一列
    df[name] = last_column


def process_LLMContextPrecisionWithoutReference(user_inputs, responses, retrieved_contexts, df):
    print("here is processing")
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


def rag_list() -> list[dict]:
    return [{'name': '基于大模型的无参考上下文准确性', 'description': '使用大模型评估Rag上下文的准确性，没有参考答案'},
            {'name': '基于大模型的有参考上下文准确性', 'description': '使用大模型评估Rag上下文的准确性，拥有参考答案'},
            {'name': '有参考上下文准确性', 'description': '评估Rag上下文的准确性，拥有参考答案'},
            {'name': '基于大模型的上下文召回率', 'description': '使用大模型评估Rag上下文的召回率'},
            {'name': '上下文召回率', 'description': '评估Rag上下文的召回率'},
            {'name': '上下文实体召回率', 'description': '评估Rag上下文实体的召回率'},
            {'name': '噪声敏感度', 'description': '评估Rag系统的噪声敏感度'},
            {'name': '回答相关性', 'description': '评估Rag的回答与上下文的相关性'},
            {'name': '置信度', 'description': '评估Rag的回答与上下文的置信度'},
            {'name': '带幻觉检测的置信度', 'description': '评估置信度，同时考虑幻觉'},
            {'name': '回答准确率', 'description': '评估Rag回答的准确率'},
            {'name': '上下文相关性', 'description': '评估上下文与输入之间的相关性'},
            {'name': '响应扎根性', 'description': '评估回答与上下文之间的扎根性'},
            {'name': '事实准确性', 'description': '根据参考评估回答的准确性'},
            {'name': '语义相似性', 'description': '评估回答与参考之间的语义相似性'},
            {'name': '字符串相似度', 'description': '评估回答与参考之间的字符串相似度'},
            {'name': 'Bleu分数', 'description': '评估回答与参考之间的Bleu分数'},
            {'name': 'Rouge分数', 'description': '评估回答与参考之间的Rouge分数'},
            {'name': '摘要得分', 'description': '评估回答从上下文中获取关键信息的能力'}]
