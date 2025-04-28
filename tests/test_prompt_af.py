import pytest
from unittest.mock import patch, MagicMock
import re
from prompt.auto_fill import fill_prompt, fill_with_LLM

# Import the functions to test


@pytest.fixture
def mock_evaluation():
    """Create a mock PromptEvaluation object"""
    mock = MagicMock()
    mock.input_text = "Hello, {name}. Today is {date}."
    return mock


@pytest.fixture
def mock_get_completion():
    """Mock the get_completion function"""
    with patch("prompt.auto_fill.get_completion") as mock:
        yield mock


class TestFillPrompt:

    def test_manual_fill(self, mock_evaluation):
        """Test fill_prompt with manual autofill option"""
        # Setup
        mock_evaluation.autofill = "manual"
        mock_evaluation.user_fill = "John Doe;2023-06-15"

        # Execute
        fill_prompt(mock_evaluation)

        # Assert
        assert mock_evaluation.input_text == "Hello, John Doe. Today is 2023-06-15."

    def test_manual_fill_with_chinese_separator(self, mock_evaluation):
        """Test fill_prompt with manual autofill using Chinese separator"""
        # Setup
        mock_evaluation.autofill = "manual"
        mock_evaluation.user_fill = "张三；2023年6月15日"

        # Execute
        fill_prompt(mock_evaluation)

        # Assert
        assert mock_evaluation.input_text == "Hello, 张三. Today is 2023年6月15日."

    @patch("prompt.auto_fill.fill_with_LLM")
    def test_auto_fill(self, mock_fill_with_llm, mock_evaluation):
        """Test fill_prompt with auto autofill option"""
        # Setup
        mock_evaluation.autofill = "auto"
        mock_fill_with_llm.return_value = "Hello, AI Assistant. Today is 2023-06-15."

        # Execute
        it = mock_evaluation.input_text
        fill_prompt(mock_evaluation)

        # Assert
        mock_fill_with_llm.assert_called_once_with(it)
        assert mock_evaluation.input_text == "Hello, AI Assistant. Today is 2023-06-15."


class TestFillWithLLM:

    def test_successful_fill(self, mock_get_completion):
        """Test fill_with_LLM with successful completion"""
        # Setup
        test_prompt = "Hello, {name}!"
        mock_get_completion.return_value = "Hello, John!"

        # Execute
        result = fill_with_LLM(test_prompt)

        # Assert
        assert result == "Hello, John!"
        mock_get_completion.assert_called_once()
        # Check that the template was used correctly
        call_args = mock_get_completion.call_args[0][0]
        assert "你是一个Prompt自动填充助手" in call_args
        assert test_prompt in call_args

    def test_error_handling(self, mock_get_completion):
        """Test fill_with_LLM error handling"""
        # Setup
        mock_get_completion.side_effect = Exception("API error")

        # Execute
        result = fill_with_LLM("Hello, {name}!")

        # Assert
        assert "填充失败" in result
        assert "API error" in result

    def test_complex_placeholders(self, mock_get_completion):
        """Test fill_with_LLM with complex placeholders"""
        # Setup
        test_prompt = "User {user_id} accessed {feature_name} on {access_date}"
        filled_text = "User 12345 accessed Dashboard on 2023-06-15"
        mock_get_completion.return_value = filled_text

        # Execute
        result = fill_with_LLM(test_prompt)

        # Assert
        assert result == filled_text
