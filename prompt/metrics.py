from langchain_core.prompts import PromptTemplate
from zhipuai import ZhipuAI

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

def get_completion(prompt,model="glm-4-flash",temperature=0):
    api_key = os.environ.get('API_KEY')
    client = ZhipuAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
    )
    if len(response.choices) > 0:
        return response.choices[0].message.content
    else:
        return "generate answer error"


class Metric:
    def __init__(self):
        self.metric = ""
        self.prompt = ""
        self.answer = ""

    def evaluate(self,prompt):
        pass


# 知识查找正确性
class knowledgeSearchCorrectnessMetric(Metric):
    def evaluate(self,prompt):
        self.prompt = prompt
        self.metric = '''知识查找正确性。评估系统给定的知识片段是否能够对问题做出回答。如果知识片段不能做出回答，打分为0；如果知识片段可以做出回答，打分为1。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=self.prompt,
            answer=self.answer
        ))
        return response


# 回答一致性
class answerAdherenceMetric(Metric):
    def evaluate(self,prompt):
        self.metric = '''回答一致性。评估系统的回答是否针对用户问题展开，是否有偏题、错误理解题意的情况，打分分值在0~1之间，0为完全偏题，1为完全切题。'''

        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=self.prompt,
            answer=self.answer
        ))
        return response


class DefinitionMetric(Metric):
    def __init__(self,metric:str):
        super().__init__()
        self.metric = metric

    def evaluate(self,prompt):
        self.answer = get_completion(self.prompt)

        final_prompt = PromptTemplate(input_variables=["metric","prompt","answer"],
                                      template=metric_prompt
                                      )
        response = get_completion(final_prompt.format(
            metric=self.metric,
            prompt=self.prompt,
            answer=self.answer
        ))

        return response





