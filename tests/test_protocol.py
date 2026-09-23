import unittest

from a2a.messages import VALID_CATEGORIES, completed
from a2a.protocol import TaskResult, TaskStatus, TaskStore


class ProtocolTests(unittest.TestCase):
    def test_task_store_tracks_typed_result(self):
        store = TaskStore()
        task = store.submit("Cannot connect to Wi-Fi", task_id="task-1")
        result = TaskResult("network", "Restart the approved network service.", ["network.md"])
        store.update(task.task_id, TaskStatus.COMPLETED, result=result)

        saved = store.get("task-1")
        self.assertEqual(saved.status, TaskStatus.COMPLETED)
        self.assertEqual(saved.result.category, "network")

    def test_contract_rejects_unknown_category(self):
        with self.assertRaises(ValueError):
            completed("task-1", TaskResult("email", "Use the approved procedure."))

    def test_categories_are_explicit(self):
        self.assertEqual(VALID_CATEGORIES, {"account_access", "hardware", "software", "network"})


if __name__ == "__main__":
    unittest.main()