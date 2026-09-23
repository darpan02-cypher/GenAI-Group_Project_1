import unittest

from a2a.protocol import TaskResult, TaskStatus, TaskStore
from requester_agent.agent import RequesterAgent, TaskFailedError


class FakeSpecialist:
    def __init__(self, store, status):
        self.store = store
        self.status = status

    def receive_task(self, payload):
        task = self.store.submit(payload["question"], task_id="fake-task")
        if self.status == TaskStatus.COMPLETED:
            self.store.update(task.task_id, self.status, TaskResult("software", "Restart the app."))
        else:
            self.store.update(task.task_id, self.status, error="test failure")
        return {"task_id": task.task_id, "status": TaskStatus.SUBMITTED.value}


class RequesterTests(unittest.TestCase):
    def test_requester_returns_result_without_knowing_rag_details(self):
        store = TaskStore()
        requester = RequesterAgent(FakeSpecialist(store, TaskStatus.COMPLETED), store, poll_interval=0, timeout=1)
        self.assertEqual(requester.handle_user_request("Install app")["category"], "software")

    def test_requester_surfaces_failure(self):
        store = TaskStore()
        requester = RequesterAgent(FakeSpecialist(store, TaskStatus.FAILED), store, poll_interval=0, timeout=1)
        with self.assertRaises(TaskFailedError):
            requester.handle_user_request("Install app")


if __name__ == "__main__":
    unittest.main()