import pytest
from unittest.mock import patch, MagicMock
import json
from prompt.optimizer import optimize_prompt


def test_optimize_prompt_success():
    """Test successful prompt optimization."""
    # Mock response data
    mock_response = '["Optimized prompt", "This is the optimization reason"]'

    # Mock the get_completion function
    with patch("prompt.optimizer.get_completion", return_value=mock_response):
        result = optimize_prompt(
            "Original prompt", {"clarity": 3.0, "effectiveness": 1.5}
        )

    assert result == {
        "optimized_prompt": "Optimized prompt",
        "reason": "This is the optimization reason",
    }


def test_optimize_prompt_lowest_score_selection():
    """Test that the function selects the reason with the lowest score."""
    mock_response = '["Optimized prompt", "Optimization reason"]'

    with patch("prompt.optimizer.get_completion") as mock_get_completion:
        # Call the function with a score dictionary
        optimize_prompt(
            "Original prompt", {"clarity": 3.0, "effectiveness": 1.5, "relevance": 4.0}
        )

        # Check that the call includes the reason with the lowest score
        args, _ = mock_get_completion.call_args
        assert "effectiveness" in args[0]


def test_optimize_prompt_json_decode_error():
    """Test handling of JSON decode errors."""
    # Mock an invalid JSON response
    with patch("prompt.optimizer.get_completion", return_value="Invalid JSON"):
        result = optimize_prompt("Original prompt", {"clarity": 3.0})

    assert "error" in result
    assert "JSON解析失败" in result["error"]
    assert result["raw"] == "Invalid JSON"


def test_optimize_prompt_format_error():
    """Test handling of incorrect format (not a list of length 2)."""
    # Mock response with incorrect format
    with patch("prompt.optimizer.get_completion", return_value='["Single item"]'):
        result = optimize_prompt("Original prompt", {"clarity": 3.0})

    assert "error" in result
    assert "格式错误" in result["error"]


def test_optimize_prompt_general_exception():
    """Test handling of general exceptions."""
    # Mock get_completion to raise an exception
    with patch("prompt.optimizer.get_completion", side_effect=Exception("Test error")):
        result = optimize_prompt("Original prompt", {"clarity": 3.0})

    assert "error" in result
    assert "优化失败" in result["error"]
    assert "Test error" in result["error"]
