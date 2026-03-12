"""Tests for the state store module.

Tests cover both the _NoOpStore fallback and StateStore with live Redis.
Live Redis tests are skipped when Redis is unavailable.
"""

from __future__ import annotations

import socket
import unittest

from local_agents.state import (
    StateStore,
    _NoOpStore,
    connect,
    list_runs,
    load_result,
    load_stage,
    save_result,
    save_stage,
)


def _redis_available() -> bool:
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(("localhost", 6379))
        return True
    except (OSError, ConnectionError, TimeoutError):
        return False
    finally:
        if sock:
            try:
                sock.close()
            except OSError:
                pass


class NoOpStoreTests(unittest.TestCase):
    """Tests for the graceful-degradation fallback store."""

    def test_available_is_false(self) -> None:
        store = _NoOpStore()
        self.assertFalse(store.available)

    def test_set_returns_false(self) -> None:
        store = _NoOpStore()
        self.assertFalse(store.set("key", {"data": 1}))

    def test_get_returns_none(self) -> None:
        store = _NoOpStore()
        self.assertIsNone(store.get("key"))

    def test_delete_returns_false(self) -> None:
        store = _NoOpStore()
        self.assertFalse(store.delete("key"))

    def test_keys_returns_empty(self) -> None:
        store = _NoOpStore()
        self.assertEqual(store.keys(), [])

    def test_close_is_safe(self) -> None:
        store = _NoOpStore()
        store.close()  # should not raise


class ConnectFallbackTests(unittest.TestCase):
    """Tests that connect() returns NoOpStore when Redis is down."""

    def test_bad_port_returns_noop(self) -> None:
        store = connect(host="localhost", port=1)
        self.assertFalse(store.available)
        self.assertIsInstance(store, _NoOpStore)


class PipelineHelperNoOpTests(unittest.TestCase):
    """Pipeline state helpers should be safe with NoOpStore."""

    def test_save_and_load_stage_noop(self) -> None:
        store = _NoOpStore()
        save_stage(store, "run-1", "triage", {"priority": "p1"})
        self.assertIsNone(load_stage(store, "run-1", "triage"))

    def test_save_and_load_result_noop(self) -> None:
        store = _NoOpStore()
        save_result(store, "run-1", {"pipeline_status": "ok"})
        self.assertIsNone(load_result(store, "run-1"))

    def test_list_runs_noop(self) -> None:
        store = _NoOpStore()
        self.assertEqual(list_runs(store), [])


@unittest.skipUnless(_redis_available(), "Redis not available on localhost:6379")
class LiveRedisTests(unittest.TestCase):
    """Integration tests that require a running Redis instance."""

    def setUp(self) -> None:
        self.store = connect()
        self.assertTrue(self.store.available)
        # Clean up test keys
        for key in self.store.keys("test:state:*"):
            self.store.delete(key)

    def tearDown(self) -> None:
        for key in self.store.keys("test:state:*"):
            self.store.delete(key)
        self.store.close()

    def test_set_and_get(self) -> None:
        data = {"priority": "p1", "category": "access"}
        self.assertTrue(self.store.set("test:state:simple", data))
        result = self.store.get("test:state:simple")
        self.assertEqual(result, data)

    def test_get_missing_key(self) -> None:
        self.assertIsNone(self.store.get("test:state:nonexistent"))

    def test_delete(self) -> None:
        self.store.set("test:state:delete-me", {"x": 1})
        self.assertTrue(self.store.delete("test:state:delete-me"))
        self.assertIsNone(self.store.get("test:state:delete-me"))

    def test_delete_missing(self) -> None:
        self.assertFalse(self.store.delete("test:state:never-existed"))

    def test_keys_pattern(self) -> None:
        self.store.set("test:state:a", {"a": 1})
        self.store.set("test:state:b", {"b": 2})
        keys = self.store.keys("test:state:*")
        self.assertIn("test:state:a", keys)
        self.assertIn("test:state:b", keys)

    def test_ttl_short(self) -> None:
        self.store.set("test:state:ttl", {"t": 1}, ttl=1)
        result = self.store.get("test:state:ttl")
        self.assertEqual(result, {"t": 1})

    def test_complex_value(self) -> None:
        data = {
            "triage": {"priority": "p1", "category": "access"},
            "draft": {"subject": "Re: Login issue", "reply": "We are investigating."},
            "pipeline_status": "ok",
        }
        self.store.set("test:state:complex", data)
        result = self.store.get("test:state:complex")
        self.assertEqual(result, data)


@unittest.skipUnless(_redis_available(), "Redis not available on localhost:6379")
class LivePipelineHelperTests(unittest.TestCase):
    """Pipeline helper tests against live Redis."""

    def setUp(self) -> None:
        self.store = connect()
        for key in self.store.keys("pipeline:test-run-*"):
            self.store.delete(key)

    def tearDown(self) -> None:
        for key in self.store.keys("pipeline:test-run-*"):
            self.store.delete(key)
        self.store.close()

    def test_save_and_load_stage(self) -> None:
        stage_data = {"priority": "p2", "category": "billing"}
        save_stage(self.store, "test-run-1", "triage", stage_data)
        loaded = load_stage(self.store, "test-run-1", "triage")
        self.assertEqual(loaded, stage_data)

    def test_save_and_load_result(self) -> None:
        result_data = {"pipeline_status": "ok", "triage": {"priority": "p1"}}
        save_result(self.store, "test-run-2", result_data)
        loaded = load_result(self.store, "test-run-2")
        self.assertEqual(loaded, result_data)

    def test_list_runs(self) -> None:
        save_result(self.store, "test-run-a", {"status": "ok"})
        save_result(self.store, "test-run-b", {"status": "ok"})
        runs = list_runs(self.store)
        self.assertIn("test-run-a", runs)
        self.assertIn("test-run-b", runs)

    def test_multiple_stages_per_run(self) -> None:
        save_stage(self.store, "test-run-3", "triage", {"priority": "p1"})
        save_stage(self.store, "test-run-3", "reply", {"subject": "test"})
        save_result(self.store, "test-run-3", {"status": "ok"})
        self.assertEqual(load_stage(self.store, "test-run-3", "triage"), {"priority": "p1"})
        self.assertEqual(load_stage(self.store, "test-run-3", "reply"), {"subject": "test"})
        self.assertEqual(load_result(self.store, "test-run-3"), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
