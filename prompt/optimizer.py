from prompt.metrics import get_completion
import json
optimize_prompt_template = '''
你是一个Prompt优化专家。

我会给你一个原始Prompt和其在多个指标下的评估得分。请你优化这个Prompt，使得它在这些指标下的表现更好。

请返回一个JSON数组，格式如下：
["优化后的Prompt", "优化理由"]

不要输出任何其他内容！

原始Prompt：
~~~
{prompt}
~~~

指标与得分：
{score_dict}
'''

def optimize_prompt(prompt: str, score_dict: dict[str,float]) -> dict:
    score_text = '\n'.join([f"{k}: {v}" for k, v in score_dict.items()])
    response = get_completion(optimize_prompt_template.format(prompt = prompt,score_dict = score_text))

    #解析
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list) and len(parsed) == 2:
            return {
                "optimized_prompt": parsed[0],
                "reason": parsed[1]
            }
        else:
            return {"error": "格式错误，非长度为2的列表", "raw": response}
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败：{e}", "raw": response}
