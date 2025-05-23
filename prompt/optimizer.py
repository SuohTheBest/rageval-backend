from prompt.utils import get_completion
import json

optimize_prompt_template = '''
你是一个专业的 Prompt模板 优化专家，擅长理解用户需求并基于指定评估理由优化prompt模板。

请按照以下规则进行优化：
- 保留所有变量占位符，不要省略它们。
- 优化语言表达，使其更具体、清晰、富有逻辑性，但不得删减或替换任何变量。
- 优化后的 Prompt 应完整保留原始任务目标，不可省略任何重要输入变量或任务步骤。
- 优化应以“重构”优先，而非“压缩”优先，适度增加细节和具体性。
- 若原始 Prompt 较长，优化后长度不应缩短超过30%，应增强逻辑与语义而非简化结构。

注意!!!:
- 输出字符串包含两部分:优化后的prompt模板和理由，之间用“@@@@@”分隔,如"XXXX@@@@@XXXX"。

任务流程：
1. 仔细阅读原始Prompt。
2. 根据提供的评估理由（{reason}）分析改进方向。
3. 优化Prompt并清晰说明优化理由。

原始Prompt：
~~~
{prompt}
~~~

输出示例：
{example}

'''

def optimize_prompt(prompt: str, score_dict: dict[str, float]) -> dict:
    # 找到得分最低的指标
    lowest_score = min(score_dict.values())
    example = """
~~~\n# 作为问题推荐助手，你的任务是依据<题目>、<解析>以及老师和学生的<答疑内容>，深入分析学生的思维过程，准确推测学生可能提出的后续问题\n\n1. 仔细研读<题目>、<解析>和<答疑内容>，把握学生的思考方向，识别学生的理解难点\n2. 生成三条符合学生思路的推测问题，每条问题字数限制在10字以内\n3. 确保推测问题与学生的思路和题目背景相契合\n\n<题目>：{question}\n<解析>：{analysis}\n\n<答疑内容>：{dialog}\n\n@@@@@\n
在任务描述中加入了“深入分析学生的思维过程”和“准确推测学生可能提出的后续问题”，以强调对学生思路的准确把握，将“推测学生的理解盲区”改为“识别学生的理解难点”，使描述更具体、更贴近实际教学场景，在输出要求中，强调了推测问题需与学生的思路和题目背景相契合，确保推测问题的相关性。
  """
    reason = ''
    print(example)
    print("==============================")
    for r,score in score_dict.items():
        if score == lowest_score:
            reason = r

    try:
        response = get_completion(optimize_prompt_template.format(
            prompt=prompt,
            reason=reason,
            example = example
        ))
        print(response)
        parsed = response.split("@@@@@")
        print("==============================")
        print(parsed)
        return {"optimized_prompt": parsed[0], "reason": parsed[1]}

    except Exception as e:
        return {"error": f"优化失败：{e}"}
