from prompt.metrics import DefinitionMetric


def create_custom_metric(metric_definition: str) -> Metric:
    return DefinitionMetric(metric_definition)
