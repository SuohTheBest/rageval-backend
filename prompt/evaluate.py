import ast

from models.Task import PromptEvaluation
from prompt.metrics import Metric, create_custom_metric
from prompt.metrics import (
    liquidityMetric, ethicalMetric, clarityMetric, robustnessMetric, 
    safeMetric, effectiveMetric, metricDesignMetric, riskControlMetric, 
    extensionMetric
)

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
        "自定义": None
    }

    if evaluation.method == "自定义":
        metric_instance = create_custom_metric(evaluation.custom_method)
    else:
        metric_class = metric_mapping.get(evaluation.method)
        metric_instance = metric_class()

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