from prompt.metrics import Metric

#使用指标来评估prompt
def evaluate_prompt(prompt: str, metrics: list[Metric]) -> dict[str, float]:
    results = {}
    for metric in metrics:
        score = metric.evaluate(prompt)
        results[metric.metric] = score
    return results