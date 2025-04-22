from prompt.metrics import get_completion

autofill_template = '''
请你根据上下文补全以下Prompt中的占位符（用花括号括起来的内容）。

原始prompt：
~~~
{prompt}
~~~

你应该合理替换所有占位符，比如 {username} 替换成用户名字。
请你直接返回填充后的prompt，不要输出其他内容。
'''

def autofill_prompt(prompt: str) -> str:
    filled_prompt = autofill_template.format(prompt=prompt)
    return get_completion(filled_prompt)