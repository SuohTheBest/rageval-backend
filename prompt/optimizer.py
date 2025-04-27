from prompt.utils import get_completion
import json

optimize_prompt_template = '''
你是一个Prompt优化专家。

我会给你一个原始Prompt,请你结合评估理由来优化这个Prompt，评估理由如下：
{reason}。

请返回一个JSON数组，格式如下：
["优化后的Prompt", "优化理由"]

不要输出任何其他内容！

原始Prompt：
~~~
{prompt}
~~~

'''

def optimize_prompt(prompt: str, score_dict: dict[str, float]) -> dict:
    # 找到得分最低的指标
    lowest_score = min(score_dict.values())
    reason = ''
    for r,score in score_dict.items():
        if score == lowest_score:
            reason = r

    try:
        response = get_completion(optimize_prompt_template.format(
            prompt=prompt,
            reason=reason
        ))
        parsed = json.loads(response)
        if isinstance(parsed, list) and len(parsed) == 2:
            return {"optimized_prompt": parsed[0], "reason": parsed[1]}
        return {"error": "格式错误，非长度为2的列表", "raw": response}
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败：{e}", "raw": response}
    except Exception as e:
        return {"error": f"优化失败：{e}"}
