import pytest
from unittest.mock import patch, Mock, MagicMock
import pandas as pd
import os
from rag_eval.ragas_metrics import process_rag
from models.Task import RAGEvaluation, OutputFile


@pytest.fixture
def mock_evaluation():
    """Create a mock RAGEvaluation object."""
    eval_mock = Mock(spec=RAGEvaluation)
    eval_mock.id = 123
    eval_mock.input_id = "test_input_id"
    eval_mock.method = "基于大模型的无参考上下文准确性"
    return eval_mock


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db_mock = Mock()
    db_mock.add = Mock()
    db_mock.commit = Mock()
    db_mock.close = Mock()
    return db_mock


@pytest.fixture
def mock_dataframe():
    """Create a mock DataFrame with test data."""
    data = {
        "user_input": ["What is Python?", "How does ML work?"],
        "response": ["Python is a programming language", "ML uses algorithms"],
        "reference": ["Python is high-level", "ML learns from data"],
        "retrieved_contexts": ["['Context about Python']", "['Context about ML']"],
        "reference_contexts": ["['Reference context']", "['Reference context']"],
        "score": [0.8, 0.9],  # Score column to simulate result
    }
    return pd.DataFrame(data)


@patch("rag_eval.ragas_metrics.os")
@patch("task.utils.get_upload_filepath")
@patch("pandas.read_csv")
@patch("rag_eval.ragas_metrics.process_LLMContextPrecisionWithoutReference")
def test_process_rag_llm_context_precision_without_reference(
    mock_processor,
    mock_read_csv,
    mock_get_filepath,
    mock_os,
    mock_evaluation,
    mock_db,
    mock_dataframe,
):
    """Test process_rag with LLMContextPrecisionWithoutReference method."""
    user_id = "test_user_id"
    mock_get_filepath.return_value = "test_file_path"
    mock_read_csv.return_value = mock_dataframe
    mock_os.path.getsize.return_value = 1024

    result = process_rag(mock_evaluation, mock_db, user_id)

    mock_get_filepath.assert_called_once_with(mock_evaluation.input_id)
    mock_read_csv.assert_called_once_with("test_file_path")
    mock_processor.assert_called_once()
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called()
    mock_db.close.assert_called_once()
    assert result == mock_dataframe.iloc[:, -1].mean()
    assert mock_evaluation.output_text == mock_dataframe.iloc[:, -1].mean()


@patch("rag_eval.ragas_metrics.os")
@patch("task.utils.get_upload_filepath")
@patch("pandas.read_csv")
@patch("rag_eval.ragas_metrics.process_LLMContextPrecisionWithReference")
def test_process_rag_llm_context_precision_with_reference(
    mock_processor,
    mock_read_csv,
    mock_get_filepath,
    mock_os,
    mock_evaluation,
    mock_db,
    mock_dataframe,
):
    """Test process_rag with LLMContextPrecisionWithReference method."""
    user_id = "test_user_id"
    mock_evaluation.method = "基于大模型的有参考上下文准确性"
    mock_get_filepath.return_value = "test_file_path"
    mock_read_csv.return_value = mock_dataframe
    mock_os.path.getsize.return_value = 1024

    result = process_rag(mock_evaluation, mock_db, user_id)

    mock_processor.assert_called_once()
    assert result == mock_dataframe.iloc[:, -1].mean()


@patch("rag_eval.ragas_metrics.os")
@patch("task.utils.get_upload_filepath")
@patch("pandas.read_csv")
@patch("rag_eval.ragas_metrics.process_NonLLMContextPrecisionWithReference")
def test_process_rag_non_llm_context_precision(
    mock_processor,
    mock_read_csv,
    mock_get_filepath,
    mock_os,
    mock_evaluation,
    mock_db,
    mock_dataframe,
):
    """Test process_rag with NonLLMContextPrecisionWithReference method."""
    user_id = "test_user_id"
    mock_evaluation.method = "有参考上下文准确性"
    mock_get_filepath.return_value = "test_file_path"
    mock_read_csv.return_value = mock_dataframe
    mock_os.path.getsize.return_value = 1024

    result = process_rag(mock_evaluation, mock_db, user_id)

    mock_processor.assert_called_once()
    assert result == mock_dataframe.iloc[:, -1].mean()


@patch("rag_eval.ragas_metrics.os")
@patch("task.utils.get_upload_filepath")
@patch("pandas.read_csv")
@patch("rag_eval.ragas_metrics.OutputFile")
@patch("rag_eval.ragas_metrics.process_BleuScore")
def test_process_rag_file_output(
    mock_processor,
    mock_output_file,
    mock_read_csv,
    mock_get_filepath,
    mock_os,
    mock_evaluation,
    mock_db,
    mock_dataframe,
):
    """Test process_rag file output handling with BleuScore method."""
    user_id = "test_user_id"
    mock_evaluation.method = "Bleu分数"
    mock_get_filepath.return_value = "test_file_path"
    mock_read_csv.return_value = mock_dataframe
    mock_os.path.getsize.return_value = 1024

    output_file_instance = Mock()
    output_file_instance.id = 456
    mock_output_file.return_value = output_file_instance

    result = process_rag(mock_evaluation, mock_db, user_id)

    mock_output_file.assert_called_once_with(user_id=user_id, file_name="temp", size=0)
    mock_db.add.assert_called_once_with(output_file_instance)
    assert mock_evaluation.output_id == 456
    assert result == mock_dataframe.iloc[:, -1].mean()
