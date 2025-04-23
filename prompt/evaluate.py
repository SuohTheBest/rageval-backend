from prompt.metrics import Metric

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
