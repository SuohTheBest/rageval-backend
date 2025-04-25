from langchain_core.prompts import PromptTemplate
from prompt.utils import get_completion

metric_prompt = '''
你是一个prompt评估员。
接下来，我将给你一个prompt和模型对prompt的回答。
请你评估以下维度该prompt的表现，给出打分：

{metric}

你应该是比较严苛的评估员，很少给出满分的高评估。
prompt：
~~~
{prompt}
~~~
待评估的回答：
~~~
{answer}
~~~
你应该返回给我一个数字，值是该维度对应的评估打分。
不要输出任何其他内容。
'''


import os

os.environ["API_KEY"] = "2ac574e73afa430fb225aa3fb48a6fc9.wHZ6jqzAD6ahuEMX"


class Metric:
    def __init__(self):
        self.metric = ""
        self.answer = ""

    def evaluate(self,prompt,answer):
        pass


class DefinitionMetric(Metric):
        def __init__(self, metric: str):
            super().__init__()
            self.metric = metric

        def evaluate(self, prompt,answer):
            final_prompt = PromptTemplate(input_variables=["metric", "prompt", "answer"],
                                          template=metric_prompt
                                          )
            response = get_completion(final_prompt.format(
                metric=self.metric,
                prompt=prompt,
                answer=answer
            ))

            return response


# 知识查找正确性
class answerCorrectnessMetric(Metric):
    def evaluate(self,prompt,answer):
        self.prompt = prompt
        self.metric = '''回答正确性。该维度评估系统回答是否正确，是否充分解答了用户问题，打分分值在0~1之间，0为完全不正确，1为完全正确。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
            answer=answer
        ))
        return response


# 回答一致性
class answerAdherenceMetric(Metric):
    def evaluate(self,prompt,answer):
        self.metric = '''回答一致性。评估系统的回答是否针对用户问题展开，是否有偏题、错误理解题意的情况，打分分值在0~1之间，0为完全偏题，1为完全切题。'''

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
            answer=answer
        ))
        return response


# 逻辑性
class logicalityMetric(Metric):
    def evaluate(self,prompt,answer):
        self.metric = '''逻辑性。该维度评估系统回答是否逻辑连贯，是否出现前后冲突、逻辑混乱的情况。打分分值在0~1之间，0为逻辑完全混乱，1为完全没有逻辑问题。'''

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
            answer=answer
        ))
        return response


# 通顺性
class liquidityMetric(Metric):
    def evaluate(self,prompt,answer):
        self.metric = '''通顺性。该维度评估系统回答是否通顺、合乎语法。打分分值在0~1之间，0为语句完全不通顺，1为语句完全通顺没有任何语法问题。'''

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
            answer=answer
        ))
        return response


# 智能性
class intelligenceMetric(Metric):
    def evaluate(self,prompt,answer):
        self.metric = '''智能性。该维度评估系统回答是否拟人化、智能化，是否能充分让用户混淆人工回答与智能回答。打分分值在0~1之间，0为非常明显的模型回答，1为与人工回答高度一致。'''

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
            answer=answer
        ))
        return response




# 用户自定义指标
def create_custom_metric(metric_definition: str) -> Metric:
    try:
        return DefinitionMetric(metric_definition)
    except Exception as e:
        raise ValueError(f"自定义指标创建失败：{e}")


# 使用指标来评估prompt
def evaluate_prompt(prompt: str, metrics: list[Metric]) -> dict[str, float]:
    results = {}
    for metric in metrics:
        score = metric.evaluate(prompt)
        results[metric.metric] = score
    return results
