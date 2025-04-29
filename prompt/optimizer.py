from prompt.utils import get_completion
import json

optimize_prompt_template = '''
你是一个专业的 Prompt 优化专家，擅长理解用户需求并基于指定评估理由优化提示词。

请按照以下规则进行优化：
- 优化后的 Prompt 应完整保留原始任务目标，不可省略任何重要输入变量或任务步骤。
- 优化应以“重构”优先，而非“压缩”优先，适度增加细节和具体性。
- 若原始 Prompt 较长，优化后长度不应缩短超过30%，应增强逻辑与语义而非简化结构。
- 输出结构必须为一个 列表，包含两个元素：优化后的Prompt和优化理由。
- 禁止输出除列表外的任何文字或解释。

任务流程：
1. 仔细阅读原始Prompt。
2. 根据提供的评估理由（{reason}）分析改进方向。
3. 优化Prompt并清晰说明优化理由。

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
        print(response)
        parsed = json.loads(response)
        if isinstance(parsed, list) and len(parsed) == 2:
            return {"optimized_prompt": parsed[0], "reason": parsed[1]}
        return {"error": "格式错误，非长度为2的列表", "raw": response}
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败：{e}", "raw": response}
    except Exception as e:
        return {"error": f"优化失败：{e}"}
