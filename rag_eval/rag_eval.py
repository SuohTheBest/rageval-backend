# import asyncio

# from ragas import evaluate
from langchain_openai import ChatOpenAI
from ragas.metrics import *
import numpy as np
# rag
import pandas as pd
import os
# from ragas import SingleTurnSample, EvaluationDataset
# from ragas.metrics import BleuScore
from ragas.llms import LangchainLLMWrapper
import ast
from models.Task import RAGEvaluation, OutputFile
from rag_eval.utils import *

def process_rag(eval: RAGEvaluation, db,user_id):
    print("here is processing")
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
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
        print("method here")
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

    last_column = df.iloc[:, -1]
    average = last_column.mean()
    # 判断是否是 NaN
    if np.isnan(average):
        print("average is NaN, calling process_rag again")
        # 递归调用，但要确保数据更新
        return process_rag(eval, db, user_id)
    else:
        output_file = OutputFile(user_id=user_id, file_name='temp', size=0)
        db.add(output_file)
        db.commit()
        output_id = output_file.id
        file_path = f'downloads/{output_id}'
        output_file.file_name = f"{eval.id}_{output_id}.csv"
        df.to_csv(file_path, index=False)
        file_size = os.path.getsize(file_path)
        output_file.size = file_size
        db.commit()
        db.close()
        eval.output_id = output_id
        eval.output_text = average
        
        print(f"average: {average}")
        return average
    # if average == float('nan'):
    #     df = df.drop(df.columns[-1], axis=1)
    #     average = process_rag(eval,db,user_id)
    # else:
    #     output_file = OutputFile(user_id=user_id, file_name='temp', size=0)
    #     db.add(output_file)
    #     db.commit()
    #     output_id = output_file.id
    #     file_path = f'downloads/{output_id}'
    #     output_file.file_name=f"{eval.id}_{output_id}.csv"
    #     df.to_csv(file_path, index=False)
    #     file_size = os.path.getsize(file_path)
    #     output_file.size = file_size
    #     db.commit()
    #     db.close()
    #     eval.output_id = output_id
    #     # result = output_id
    #     eval.output_text=average
    # print(f"average:{average}")
    # return average


def set_environment():
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    return evaluator_llm



def rag_metric_list() -> list[dict]:
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
