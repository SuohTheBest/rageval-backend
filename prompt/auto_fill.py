from models.Task import PromptEvaluation
from prompt.utils import get_completion
import re

autofill_template = '''
你是一个Prompt自动填充助手。
下面是一个Prompt模板，里面有形如{{username}}、{{date}}的占位符。
请你合理地为这些字段赋值，返回填充后的Prompt内容。

Prompt模板：
~~~
{prompt}
~~~
只返回填充后的Prompt，不要输出其他内容。
'''

def fill_prompt(evaluation: PromptEvaluation):
    if evaluation.autofill == "manual":
        # 用户手动填充的内容
        parts = re.split(r'[;；]', evaluation.user_fill)
        placeholders = re.findall(r'\{[^\}]+\}', evaluation.input_text)

        for placeholder, value in zip(placeholders, parts):
            evaluation.input_text = evaluation.input_text.replace(placeholder, value,1)

    elif evaluation.autofill == "auto":
        # 系统自动填充的内容
        evaluation.input_text = fill_with_LLM(evaluation.input_text)

def fill_with_LLM(prompt: str):
    try:
        final_prompt = autofill_template.format(prompt=prompt)
        return get_completion(final_prompt)
    except Exception as e:
        return f"填充失败：{e}"

if __name__ == "__main__":
    # test
    filled = fill_with_LLM("你好，{username}，今天是{date}。")
    print("填充结果：", filled)
