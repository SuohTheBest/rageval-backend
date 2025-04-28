import ast

from sqlalchemy import func

import re
from models.Task import PromptEvaluation, Optimization
from models.database import SessionLocal
from prompt.auto_fill import fill_prompt
from prompt.metrics import Metric, create_custom_metric
from prompt.metrics import (
    liquidityMetric, ethicalMetric, clarityMetric, robustnessMetric, 
    safeMetric, effectiveMetric, metricDesignMetric, riskControlMetric, 
    extensionMetric
)
from prompt.optimizer import optimize_prompt


# 使用指标来评估prompt
def evaluate_prompt(prompt: str, metrics: list[Metric]) -> dict[str, float]:
    if not metrics:
        raise ValueError("指标列表不能为空")
    
    results = {}
    for metric in metrics:
        try:
            score = metric.evaluate(prompt)
            results[metric.metric] = score
        except Exception as e:
            results[metric.metric] = f"评估失败：{e}"
    return results

def process_prompt_task(evaluation: PromptEvaluation) -> str:
    metric_mapping = {
        "通顺性": liquidityMetric,
        "伦理合规性": ethicalMetric,
        "明确性": clarityMetric,
        "鲁棒性": robustnessMetric,
        "安全边界性": safeMetric,
        "有效性": effectiveMetric,
        "结构设计": metricDesignMetric,
        "风险控制": riskControlMetric,
        "扩展性": extensionMetric,
    }

    if evaluation.id == -1:
        db = SessionLocal()
        try:
            # 获取每个method分组的最大id及其评估结果
            subquery = (
                db.query(
                    PromptEvaluation.method,
                    func.max(PromptEvaluation.id).label("max_id"),
                    PromptEvaluation.output_text,
                    PromptEvaluation.input_text
                )
                .filter(PromptEvaluation.task_id == evaluation.task_id)
                .group_by(PromptEvaluation.method)
                .all()
            )

            r_prompt = ''
            # 提取分数并找出最低分数的指标
            score_dict = {}
            for method, _, output_text, raw_prompt in subquery:
                try:
                    # 提取分数和理由
                    score = float(output_text.split("：")[1].split("/")[0])  # 提取分数
                    reason = output_text.split("/10，")[1]  # 提取理由
                    score_dict[reason] = score
                    r_prompt = raw_prompt
                except Exception as e:
                    print(f"解析失败：{e}")


            # 调用 optimize_prompt 函数
            optimized_result = optimize_prompt(r_prompt, score_dict)
            print(f"优化结果：{optimized_result}")
            op = Optimization(task_id=evaluation.task_id, prompt=optimized_result['optimized_prompt'],reason = optimized_result['reason'])
            db.add(op)
            db.commit()

        finally:
            db.close()
        return ''

    # 填充Prompt模版
    fill_prompt(evaluation)

    # 如果是评估任务，获取对应的指标类
    try:
        metric_class = metric_mapping[evaluation.method]
        metric_instance = metric_class()
    except KeyError:
        metric_instance = create_custom_metric(evaluation.method)

    # 调用 evaluate 方法并获取返回值
    evaluation_result = metric_instance.evaluate(evaluation.input_text)

    # 解析返回的字符串为列表
    try:
        parsed_result = ast.literal_eval(evaluation_result)
        if isinstance(parsed_result, list) and len(parsed_result) == 2:
            score, reason = parsed_result
            return f"评估分数：{score}/10，{reason}"
        else:
            raise ValueError("评估结果格式不正确")
    except Exception as e:
        raise ValueError(f"解析评估结果失败：{e}")

if __name__ == "__main__":
    # 示例用法
    eval_prompt = PromptEvaluation(id= -1, task_id=2)
    process_prompt_task(eval_prompt)