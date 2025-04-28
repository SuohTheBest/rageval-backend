from prompt.utils import get_completion

autofill_template = """
你是一个Prompt自动填充助手。
下面是一个Prompt模板，里面有形如{{username}}、{{date}}的占位符。
请你合理地为这些字段赋值，返回填充后的Prompt内容。

Prompt模板：
~~~
{prompt}
~~~
只返回填充后的Prompt，不要输出其他内容。
"""


def autofill_prompt(prompt: str):
    try:
        final_prompt = autofill_template.format(prompt=prompt)
        return get_completion(final_prompt)
    except Exception as e:
        return f"填充失败：{e}"


if __name__ == "__main__":
    # test
    autofilled = autofill_prompt("你好，{username}，今天是{date}。")
    print("填充结果：", autofilled)
