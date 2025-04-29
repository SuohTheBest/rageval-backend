import pytest
from unittest.mock import patch, MagicMock
import json
from prompt.optimizer import optimize_prompt


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


def test_optimize_prompt_general_exception():
    """Test handling of general exceptions."""
    # Mock get_completion to raise an exception
    with patch("prompt.optimizer.get_completion", side_effect=Exception("Test error")):
        result = optimize_prompt("Original prompt", {"clarity": 3.0})

    assert "error" in result
    assert "优化失败" in result["error"]
    assert "Test error" in result["error"]
