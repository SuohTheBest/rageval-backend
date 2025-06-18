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
你应该返回给我一个列表，包括一个一位小数和理由，数字的值是该维度对应的评估打分。
不要输出任何其他内容。
输出请严格遵守示例中的格式,回答的开头必须为[,回答的结尾必须为]。
~~~
示例：
[7.2,"该prompt询问对RAG的看法，具有一定的开放性，可以引发对RAG的讨论和评价。但问题较为直接，缺乏引导性，追问的可能性有限，因此得分不是满分。"]
~~~
[6.3,"该prompt询问对RAG的看法，具有一定的开放性，可以引发对RAG的讨论和评价。但问题较为直接，缺乏引导性，追问的可能性有限，且RAG的具体指代不明确，可能限制对话的深度和广度。"]
'''

import os

os.environ["API_KEY"] = ""


class Metric:
    def __init__(self):
        self.metric = ""
        self.answer = ""

    def evaluate(self, prompt):
        pass


class DefinitionMetric(Metric):
    def __init__(self, metric: str):
        super().__init__()
        self.metric = metric

    def evaluate(self, prompt):
        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))

        return response


# 通顺性
class liquidityMetric(Metric):
    def evaluate(self, prompt):
        self.metric = '''通顺性。该维度评估Prompt是否通顺、合乎语法。打分分值在0~10之间，0为语句完全不通顺，10为语句完全通顺没有任何语法问题。'''

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 伦理合规性
class ethicalMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''伦理合规性。该维度评估Prompt是否符合伦理规范（如无偏见、无歧视、无有害内容），打分分值在0~10之间，0为完全不符合，10为完全符合。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 明确性
class clarityMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''明确性。该维度评估Prompt是否清晰无歧义，能否准确传达用户意图,打分分值在0~10之间，0为完全不明确，10为完全明确。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 鲁棒性
class robustnessMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''鲁棒性。该维度评估Prompt对输入噪声（如错别字、语法错误）的容忍度，打分分值在0~10之间，0为容忍度极低，10为容忍度极高。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 安全边界性
class safeMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''安全边界性。该维度评估Prompt是否能够控制输出范围，限制模型的生成内容，从而避免产生不准确的陈述，打分分值在0~10之间，0为完全不能，10为完全可以。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 有效性
class effectiveMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''有效性。该维度评估Prompt是否包含了必要的约束条件（格式/长度/风格等），使得能够引导模型生成准确、相关且有用的输出，打分分值在0~10之间，0为完全不包含，10为完全包含。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 结构设计
class metricDesignMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''结构设计。该维度评估Prompt是否包含有效的上下文铺垫及多步骤指令的逻辑连贯性，打分分值在0~10之间，0为高度不符合，10为高度符合。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 风险控制
class riskControlMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''风险控制。该维度评估Prompt是否可以规避敏感话题触发，打分分值在0~10之间，0为完全不可以，10为完全可以。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
        ))
        return response


# 扩展性
class extensionMetric(Metric):
    def evaluate(self, prompt):
        self.prompt = prompt
        self.metric = '''扩展性。该维度评估Prompt是否可以支持自然追问以及是否可以引发有价值的延伸对话，打分分值在0~10之间，0为完全不可以，10为完全可以。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric", "prompt"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=prompt,
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


def prompt_metric_list() -> list[dict]:
    return [
        {"name": "通顺性", "description": "该维度评估Prompt是否通顺、合乎语法。"},
        {"name": "伦理合规性", "description": "该维度评估Prompt是否符合伦理规范（如无偏见、无歧视、无有害内容）。"},
        {"name": "明确性", "description": "该维度评估Prompt是否清晰无歧义，能否准确传达用户意图。"},
        {"name": "鲁棒性", "description": "该维度评估Prompt对输入噪声（如错别字、语法错误）的容忍度。"},
        {"name": "安全边界性",
         "description": "安全边界性。该维度评估Prompt是否能够控制输出范围，限制模型的生成内容，从而避免产生不准确的陈述。"},
        {"name": "有效性",
         "description": "该维度评估Prompt是否包含了必要的约束条件（格式/长度/风格等）使得能够引导模型生成准确、相关且有用的输出。"},
        {"name": "结构设计", "description": "该维度评估Prompt是否包含有效的上下文铺垫及多步骤指令的逻辑连贯性。"},
        {"name": "风险控制", "description": "该维度评估Prompt是否可以规避敏感话题触发。"},
        {"name": "扩展性", "description": "该维度评估Prompt是否可以支持自然追问以及是否可以引发有价值的延伸对话。"},
    ]

# if __name__ == '__main__':
#         e = extensionMetric()
#         temp_prompt = "你觉得RAG怎么样？"
#         print(e.evaluate(
#             temp_prompt
#         ))


# # 知识查找正确性
# class answerCorrectnessMetric(Metric):
#     def evaluate(self,prompt,answer):
#         self.prompt = prompt
#         self.metric = '''回答正确性。该维度评估系统回答是否正确，是否充分解答了用户问题，打分分值在0~1之间，0为完全不正确，1为完全正确。'''
#
#         self.answer = get_completion(self.prompt)
#
#         final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
#                                       template=metric_prompt
#                                       )
#         response = get_completion(final_prompt.format(
#             metric=self.metric,
#             prompt=prompt,
#             answer=answer
#         ))
#         return response


# # 回答一致性
# class answerAdherenceMetric(Metric):
#     def evaluate(self,prompt,answer):
#         self.metric = '''回答一致性。评估系统的回答是否针对用户问题展开，是否有偏题、错误理解题意的情况，打分分值在0~1之间，0为完全偏题，1为完全切题。'''
#
#         final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
#                                       template=metric_prompt
#                                       )
#         response = get_completion(final_prompt.format(
#             metric=self.metric,
#             prompt=prompt,
#             answer=answer
#         ))
#         return response


# # 逻辑性
# class logicalityMetric(Metric):
#     def evaluate(self,prompt,answer):
#         self.metric = '''逻辑性。该维度评估系统回答是否逻辑连贯，是否出现前后冲突、逻辑混乱的情况。打分分值在0~1之间，0为逻辑完全混乱，1为完全没有逻辑问题。'''
#
#         final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
#                                       template=metric_prompt
#                                       )
#         response = get_completion(final_prompt.format(
#             metric=self.metric,
#             prompt=prompt,
#             answer=answer
#         ))
#         return response


# # 智能性
# class intelligenceMetric(Metric):
#     def evaluate(self,prompt,answer):
#         self.metric = '''智能性。该维度评估系统回答是否拟人化、智能化，是否能充分让用户混淆人工回答与智能回答。打分分值在0~1之间，0为非常明显的模型回答，1为与人工回答高度一致。'''
#
#         final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
#                                       template=metric_prompt
#                                       )
#         response = get_completion(final_prompt.format(
#             metric=self.metric,
#             prompt=prompt,
#             answer=answer
#         ))
#         return response


# # 全面性
# class completenessMetric(Metric):
#     def evaluate(self,prompt,answer):
#         self.prompt = prompt
#         self.metric = '''全面性。该维度评估系统的回答是否覆盖了问题的所有相关方面或细节，打分分值在0~1之间，0为完全不覆盖，1为完全覆盖。。'''
#
#         self.answer = get_completion(self.prompt)
#
#         final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
#                                       template=metric_prompt
#                                       )
#         response = get_completion(final_prompt.format(
#             metric=self.metric,
#             prompt=prompt,
#             answer=answer
#         ))
#         return response


# # 多样性
# class diversityMetric(Metric):
#         def evaluate(self, prompt, answer):
#             self.prompt = prompt
#             self.metric = '''多样性。该维度评估回答是否提供多样化的视角或解决方案，避免重复性、模板化的输出，打分分值在0~1之间，0为高度重复，1为高度多样性。'''
#
#             self.answer = get_completion(self.prompt)
#
#             final_prompt = PromptTemplate(input_variables=["metric", "prompt", "answer"],
#                                           template=metric_prompt
#                                           )
#             response = get_completion(final_prompt.format(
#                 metric=self.metric,
#                 prompt=prompt,
#                 answer=answer
#             ))
#             return response
