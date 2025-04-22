from prompt.metrics import DefinitionMetric, Metric

#用户自定义指标
def create_custom_metric(metric_definition: str) -> Metric:
    return DefinitionMetric(metric_definition)
