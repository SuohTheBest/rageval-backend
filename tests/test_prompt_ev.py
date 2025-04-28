import pytest
from unittest.mock import Mock, patch
from prompt.evaluate import evaluate_prompt, process_prompt_task
from prompt.metrics import Metric
from models.Task import PromptEvaluation, Optimization


def test_evaluate_prompt_normal():
    # Create mock metrics
    metric1 = Mock(spec=Metric)
    metric1.metric = "通顺性"
    metric1.evaluate.return_value = 8.5

    metric2 = Mock(spec=Metric)
    metric2.metric = "明确性"
    metric2.evaluate.return_value = 7.2

    metrics = [metric1, metric2]

    # Test the function
    result = evaluate_prompt("这是一个测试提示", metrics)

    # Check results
    assert len(result) == 2
    assert result["通顺性"] == 8.5
    assert result["明确性"] == 7.2

    # Verify metrics were called correctly
    metric1.evaluate.assert_called_once_with("这是一个测试提示")
    metric2.evaluate.assert_called_once_with("这是一个测试提示")


def test_evaluate_prompt_empty_metrics():
    with pytest.raises(ValueError, match="指标列表不能为空"):
        evaluate_prompt("这是一个测试提示", [])


def test_evaluate_prompt_metric_exception():
    metric = Mock(spec=Metric)
    metric.metric = "错误的指标"
    metric.evaluate.side_effect = Exception("测试异常")

    result = evaluate_prompt("这是一个测试提示", [metric])

    assert len(result) == 1
    assert "评估失败：测试异常" in result["错误的指标"]


@patch("prompt.evaluate.fill_prompt")
def test_process_prompt_task_normal(mock_fill_prompt):
    # Create a mock metric class
    mock_metric = Mock()
    mock_metric.evaluate.return_value = '[8.5, "理由说明"]'

    # Mock the metric class
    with patch("prompt.evaluate.liquidityMetric", return_value=mock_metric):
        evaluation = PromptEvaluation(
            id=1, task_id=1, method="通顺性", input_text="测试提示"
        )
        result = process_prompt_task(evaluation)

        assert result == "评估分数：8.5/10，理由说明"
        mock_fill_prompt.assert_called_once_with(evaluation)


@patch("prompt.evaluate.fill_prompt")
def test_process_prompt_task_invalid_result(mock_fill_prompt):
    # Mock metric with invalid return format
    mock_metric = Mock()
    mock_metric.evaluate.return_value = "不是一个有效的列表"

    with patch("prompt.evaluate.clarityMetric", return_value=mock_metric):
        evaluation = PromptEvaluation(
            id=1, task_id=1, method="明确性", input_text="测试提示"
        )

        with pytest.raises(ValueError, match="解析评估结果失败"):
            process_prompt_task(evaluation)


@patch("prompt.evaluate.fill_prompt")
def test_process_prompt_task_custom_metric(mock_fill_prompt):
    # Mock custom metric
    mock_metric = Mock()
    mock_metric.evaluate.return_value = '[7.8, "自定义指标评估"]'

    with patch("prompt.evaluate.create_custom_metric", return_value=mock_metric):
        evaluation = PromptEvaluation(
            id=1, task_id=1, method="自定义指标", input_text="测试提示"
        )
        result = process_prompt_task(evaluation)

        assert result == "评估分数：7.8/10，自定义指标评估"


@patch("prompt.evaluate.SessionLocal")
@patch("prompt.evaluate.optimize_prompt")
def test_process_prompt_task_optimization(mock_optimize_prompt, mock_session_local):
    # Set up return values
    mock_optimize_prompt.return_value = {
        "optimized_prompt": "优化后的提示",
        "reason": "优化理由",
    }

    # Mock database session and query results
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_group_by = mock_filter.group_by.return_value
    mock_group_by.all.return_value = [
        ("通顺性", 1, "评估分数：6.5/10，理由1", "原始提示"),
        ("明确性", 2, "评估分数：5.8/10，理由2", "原始提示"),
    ]

    evaluation = PromptEvaluation(id=-1, task_id=2)
    result = process_prompt_task(evaluation)

    # Verify optimization was called correctly
    mock_optimize_prompt.assert_called_once()

    # Check that Optimization was added to database
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()
