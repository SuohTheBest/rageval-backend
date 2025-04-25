from prompt.utils import get_completion
import json

optimize_prompt_template = '''
你是一个Prompt优化专家。

我会给你一个原始Prompt,请你优化这个Prompt，使得它在某个指标下的表现更好,指标如下：
{lowest_metric}。

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
    lowest_metric = min(score_dict, key=score_dict.get)
    try:
        # 在模板中插入最低指标
        response = get_completion(optimize_prompt_template.format(
            prompt=prompt,
            lowest_metric=lowest_metric,
        ))
        parsed = json.loads(response)
        if isinstance(parsed, list) and len(parsed) == 2:
            return {"optimized_prompt": parsed[0], "reason": parsed[1]}
        return {"error": "格式错误，非长度为2的列表", "raw": response}
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败：{e}", "raw": response}
    except Exception as e:
        return {"error": f"优化失败：{e}"}
