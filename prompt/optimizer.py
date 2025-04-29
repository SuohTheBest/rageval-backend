from prompt.utils import get_completion
import json

optimize_prompt_template = '''
你是一个专业的 Prompt 优化专家，擅长理解用户需求并基于指定评估理由优化提示词。

请按照以下规则进行优化：
- 保持语言简洁自然，避免冗余和歧义。
- 逻辑清晰，突出关键信息，提升执行效果。
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

请参考以下示例：

示例1：
输入原始 Prompt：
~~~
你现在是我的助手。
~~~
评估理由：缺乏角色职责和操作指引。

返回：
[
  "你是我的助手，负责整理会议记录和生成要点摘要。", 
  "补充了角色职责，使任务更明确。"
]

示例2：
输入原始 Prompt：
~~~
请写一篇文章。
~~~
评估理由：任务描述太笼统，缺乏具体要求。

返回：
[
  "请写一篇关于人工智能对教育影响的 800 字文章，需包含三个观点并举例说明。",
  "细化了主题、长度和结构要求，使生成更具针对性。"
]

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
