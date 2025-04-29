from ragas import SingleTurnSample, EvaluationDataset
from ragas import evaluate
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import *
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
    dataset = generate_dataset([reference, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ContextEntityRecall(), evaluator_llm, df, 'ContextEntityRecall')


def process_NoiseSensitivity(user_input, response, reference, retrieved_contexts, df):
    fields = ['user_input', 'response', 'reference', 'retrieved_contexts']
    dataset = generate_dataset([user_input, response, reference, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, NoiseSensitivity(), evaluator_llm, df, 'NoiseSensitivity')


def process_ResponseRelevancy(user_input, response, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = generate_dataset([user_input, response, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ResponseRelevancy(), evaluator_llm, df, 'ResponseRelevancy')


def process_Faithfulness(user_input, response, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = generate_dataset([user_input, response, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, Faithfulness(), evaluator_llm, df, 'Faithfulness')


def process_FaithfulnesswithHHEM(user_input, response, retrieved_contexts, df):
    fields = ['user_input', 'response', 'retrieved_contexts']
    dataset = generate_dataset([user_input, response, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, FaithfulnesswithHHEM(), evaluator_llm, df, 'FaithfulnesswithHHEM')


def process_AnswerAccuracy(user_input, response, reference, df):
    fields = ['user_input', 'response', 'reference']
    dataset = generate_dataset([user_input, response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, AnswerAccuracy(), evaluator_llm, df, 'AnswerAccuracy')


def process_ContextRelevance(user_input, retrieved_contexts, df):
    fields = ['user_input', 'retrieved_contexts']
    dataset = generate_dataset([user_input, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ContextRelevance(), evaluator_llm, df, 'ContextRelevance')


def process_ResponseGroundedness(response, retrieved_contexts, df):
    fields = ['response', 'retrieved_contexts']
    dataset = generate_dataset([response, retrieved_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ResponseGroundedness(), evaluator_llm, df, 'ResponseGroundedness')


def process_FactualCorrectness(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, FactualCorrectness(), evaluator_llm, df, 'FactualCorrectness')


def process_SemanticSimilarity(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, SemanticSimilarity(), evaluator_llm, df, 'SemanticSimilarity')


def process_NonLLMStringSimilarity(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, NonLLMStringSimilarity(), evaluator_llm, df, 'NonLLMStringSimilarity')


def process_BleuScore(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, BleuScore(), evaluator_llm, df, 'BleuScore')


def process_RougeScore(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, RougeScore(), evaluator_llm, df, 'RougeScore')


def process_ExactMatch(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, ExactMatch(), evaluator_llm, df, 'ExactMatch')


def process_StringPresence(response, reference, df):
    fields = ['response', 'reference']
    dataset = generate_dataset([response, reference], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, StringPresence(), evaluator_llm, df, 'StringPresence')


def process_SummarizationScore(response, reference_contexts, df):
    fields = ['response', 'reference_contexts']
    dataset = generate_dataset([response, reference_contexts], fields)
    evaluator_llm = set_environment()
    evaluate_and_store(
        dataset, SummarizationScore(), evaluator_llm, df, 'SummarizationScore')