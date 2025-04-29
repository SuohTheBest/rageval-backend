import pytest
import signal
import time
from unittest.mock import patch, MagicMock, call
from queue import Queue, Full
from multiprocessing import Event
from task.task_worker import TaskWorkerLauncher, TaskWorker
from models.Task import RAGEvaluation, PromptEvaluation, Task


class TestTaskWorkerLauncher:
    @patch("task.task_worker.TaskWorker")
    @patch("task.task_worker.signal.signal")
    def test_init(self, mock_signal, mock_task_worker):
        """Test TaskWorkerLauncher initialization"""
        launcher = TaskWorkerLauncher()

        # Check if worker was created with correct parameters
        assert mock_task_worker.called
        # Check if signal handlers were registered
        assert mock_signal.call_count == 2
        assert mock_signal.call_args_list[0][0][0] == signal.SIGINT
        assert mock_signal.call_args_list[1][0][0] == signal.SIGTERM

        # Check if worker was started
        assert launcher.worker.start.called

    @patch("task.task_worker.TaskWorker")
    @patch("task.task_worker.logger")
    def test_add_eval_success(self, mock_logger, mock_task_worker):
        """Test adding evaluation to queue successfully"""
        launcher = TaskWorkerLauncher()
        launcher.q = MagicMock()

        launcher.add_eval(1, 2, 3, "prompt")

        launcher.q.put_nowait.assert_called_once_with(
            {"id": 1, "task_id": 2, "user_id": 3, "category": "prompt"}
        )
        mock_logger.error.assert_not_called()

    @patch("task.task_worker.TaskWorker")
    @patch("task.task_worker.logger")
    def test_add_eval_queue_full(self, mock_logger, mock_task_worker):
        """Test adding evaluation to full queue"""
        launcher = TaskWorkerLauncher()
        launcher.q = MagicMock()
        launcher.q.put_nowait.side_effect = Full()

        launcher.add_eval(1, 2, 3, "prompt")

        mock_logger.error.assert_called_once()
        assert "Task queue full" in mock_logger.error.call_args[0][0]

    @patch("task.task_worker.TaskWorker")
    @patch("task.task_worker.sys.exit")
    def test_signal_handler(self, mock_exit, mock_task_worker):
        """Test signal handler"""
        launcher = TaskWorkerLauncher()
        launcher.event = MagicMock()

        launcher.signal_handler(None, None)

        launcher.event.set.assert_called_once()
        mock_exit.assert_called_once_with(0)


class TestTaskWorker:
    def test_init(self):
        """Test TaskWorker initialization"""
        queue = MagicMock()
        stop_event = MagicMock()
        engine = MagicMock()

        worker = TaskWorker(queue, stop_event, engine)

        assert worker.queue == queue
        assert worker.stop_event == stop_event
        assert worker.engine == engine

    @patch("task.task_worker.logger")
    def test_get_eval_from_queue(self, mock_logger):
        """Test getting evaluation from queue"""
        queue = MagicMock()
        queue.empty.return_value = False
        queue.get.return_value = {
            "id": 1,
            "task_id": 2,
            "user_id": 3,
            "category": "prompt",
        }

        worker = TaskWorker(queue, MagicMock(), MagicMock())
        db_session = MagicMock()

        result = worker.get_eval(db_session)

        assert result == {"id": 1, "task_id": 2, "user_id": 3, "category": "prompt"}
        queue.empty.assert_called_once()
        db_session.query.assert_not_called()

    @patch("task.task_worker.logger")
    def test_get_eval_from_db(self, mock_logger):
        """Test getting evaluation from database when queue is empty"""
        queue = MagicMock()
        queue.empty.return_value = True

        worker = TaskWorker(queue, MagicMock(), MagicMock())
        db_session = MagicMock()

        # Mock database query results
        mock_rag_eval = MagicMock(id=1, task_id=10, status="waiting")
        mock_prompt_eval = MagicMock(id=2, task_id=20, status="waiting")
        mock_task = MagicMock(user_id=100)

        db_session.query().filter().all.side_effect = [
            [mock_rag_eval],
            [mock_prompt_eval],
        ]
        db_session.get.return_value = mock_task

        worker.get_eval(db_session)

        assert queue.put_nowait.call_count >= 1
        queue.get.assert_called_once()

    @patch("task.task_worker.process_prompt_task")
    @patch("task.task_worker.logger")
    def test_process_eval_prompt(self, mock_logger, mock_process_prompt):
        """Test processing prompt evaluation"""
        mock_process_prompt.return_value = "prompt evaluation result"

        worker = TaskWorker(MagicMock(), MagicMock(), MagicMock())
        mock_eval = MagicMock()
        eval_info = {"category": "prompt", "user_id": 1, "task_id": 2}

        result = worker.process_eval(mock_eval, eval_info)

        mock_process_prompt.assert_called_once_with(mock_eval)
        assert result == {"success": True, "result": "prompt evaluation result"}
        mock_logger.info.assert_called_once()

    @patch("task.task_worker.process_rag")
    @patch("task.task_worker.logger")
    def test_process_eval_rag(self, mock_logger, mock_process_rag):
        """Test processing RAG evaluation"""
        mock_process_rag.return_value = "rag evaluation result"

        worker = TaskWorker(MagicMock(), MagicMock(), MagicMock())
        worker.session = MagicMock(return_value="db_session")
        mock_eval = MagicMock()
        eval_info = {"category": "rag", "user_id": 1, "task_id": 2}

        result = worker.process_eval(mock_eval, eval_info)

        mock_process_rag.assert_called_once_with(mock_eval, "db_session", 1)
        assert result == {"success": True, "result": "rag evaluation result"}
        mock_logger.info.assert_called_once()

    @patch("task.task_worker.logger")
    def test_process_eval_exception(self, mock_logger):
        """Test exception handling in process_eval"""
        worker = TaskWorker(MagicMock(), MagicMock(), MagicMock())
        mock_eval = MagicMock()
        eval_info = {"category": "prompt", "user_id": 1, "task_id": 2}

        with patch(
            "task.task_worker.process_prompt_task", side_effect=Exception("Test error")
        ):
            result = worker.process_eval(mock_eval, eval_info)

        assert result == {"success": False}
        mock_logger.error.assert_called_once()
        assert "Processing task failed" in mock_logger.error.call_args[0][0]

    @patch("time.time", return_value=12345)
    @patch("task.task_worker.TaskWorker.get_eval")
    @patch("task.task_worker.TaskWorker.process_eval")
    def test_run_prompt_evaluation_success(
        self, mock_process_eval, mock_get_eval, mock_time
    ):
        """Test run method for successful prompt evaluation"""
        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]  # Run once then exit

        mock_db = MagicMock()
        mock_session = MagicMock(return_value=mock_db)
        mock_eval = MagicMock(status="waiting")
        mock_db.get.return_value = mock_eval

        mock_get_eval.return_value = {
            "id": 1,
            "task_id": 2,
            "user_id": 3,
            "category": "prompt",
        }
        mock_process_eval.return_value = {"success": True, "result": "test result"}

        worker = TaskWorker(MagicMock(), stop_event, MagicMock())
        worker.session = mock_session
        worker.logger = MagicMock()

        worker.run()

        mock_get_eval.assert_called_once()
        mock_process_eval.assert_called_once()
        assert mock_eval.status == "success"
        assert mock_eval.started == 12345
        assert mock_eval.finished == 12345
        assert mock_eval.output_text == "test result"
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()
