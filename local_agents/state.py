"""Minimal Redis state store for pipeline workflow state.

Uses raw RESP protocol over stdlib sockets — no external dependencies.
Gracefully degrades to no-op when Redis is unavailable.
"""

from __future__ import annotations

import json
import socket
from typing import Any


_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 6379
_DEFAULT_TTL = 3600  # 1 hour


class _NoOpStore:
    """Fallback store that silently discards all operations."""

    @property
    def available(self) -> bool:
        return False

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return False

    def get(self, key: str) -> Any | None:
        return None

    def delete(self, key: str) -> bool:
        return False

    def keys(self, pattern: str = "*") -> list[str]:
        return []

    def close(self) -> None:
        pass


class StateStore:
    """Thin Redis client using RESP2 protocol over a raw socket."""

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        default_ttl: int = _DEFAULT_TTL,
    ) -> None:
        self._host = host
        self._port = port
        self._default_ttl = default_ttl
        self._sock: socket.socket | None = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((self._host, self._port))
            self._sock = sock
            self._send_command("PING")
            resp = self._read_response()
            self._available = resp == "PONG"
        except (OSError, ConnectionError, TimeoutError):
            self._available = False
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
            self._sock = None

    @property
    def available(self) -> bool:
        return self._available

    def _encode_command(self, *args: str) -> bytes:
        parts = [f"*{len(args)}\r\n"]
        for arg in args:
            encoded = arg.encode("utf-8")
            parts.append(f"${len(encoded)}\r\n")
            parts.append("")  # placeholder
        result = bytearray()
        arg_idx = 0
        for part in parts:
            if part == "":
                result.extend(args[arg_idx].encode("utf-8"))
                result.extend(b"\r\n")
                arg_idx += 1
            else:
                result.extend(part.encode("utf-8"))
        return bytes(result)

    def _send_command(self, *args: str) -> None:
        if not self._sock:
            return
        self._sock.sendall(self._encode_command(*args))

    def _read_response(self) -> Any:
        if not self._sock:
            return None
        return self._parse_response()

    def _read_line(self) -> str:
        buf = bytearray()
        while True:
            byte = self._sock.recv(1)  # type: ignore[union-attr]
            if not byte:
                break
            buf.extend(byte)
            if buf.endswith(b"\r\n"):
                return buf[:-2].decode("utf-8")
        return buf.decode("utf-8")

    def _parse_response(self) -> Any:
        line = self._read_line()
        if not line:
            return None
        prefix = line[0]
        data = line[1:]

        if prefix == "+":
            return data
        if prefix == "-":
            return None
        if prefix == ":":
            return int(data)
        if prefix == "$":
            length = int(data)
            if length == -1:
                return None
            content = bytearray()
            while len(content) < length + 2:
                chunk = self._sock.recv(length + 2 - len(content))  # type: ignore[union-attr]
                if not chunk:
                    break
                content.extend(chunk)
            return content[:length].decode("utf-8")
        if prefix == "*":
            count = int(data)
            if count == -1:
                return None
            return [self._parse_response() for _ in range(count)]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        if not self._available:
            return False
        try:
            serialized = json.dumps(value, sort_keys=True)
            effective_ttl = ttl if ttl is not None else self._default_ttl
            self._send_command("SET", key, serialized, "EX", str(effective_ttl))
            resp = self._read_response()
            return resp == "OK"
        except (OSError, ConnectionError):
            self._available = False
            return False

    def get(self, key: str) -> Any | None:
        if not self._available:
            return None
        try:
            self._send_command("GET", key)
            resp = self._read_response()
            if resp is None:
                return None
            return json.loads(resp)
        except (OSError, ConnectionError, json.JSONDecodeError):
            self._available = False
            return None

    def delete(self, key: str) -> bool:
        if not self._available:
            return False
        try:
            self._send_command("DEL", key)
            resp = self._read_response()
            return isinstance(resp, int) and resp > 0
        except (OSError, ConnectionError):
            self._available = False
            return False

    def keys(self, pattern: str = "*") -> list[str]:
        if not self._available:
            return []
        try:
            self._send_command("KEYS", pattern)
            resp = self._read_response()
            if isinstance(resp, list):
                return [k for k in resp if isinstance(k, str)]
            return []
        except (OSError, ConnectionError):
            self._available = False
            return []

    def close(self) -> None:
        if self._sock:
            try:
                self._send_command("QUIT")
                self._read_response()
            except (OSError, ConnectionError):
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            self._available = False


def connect(
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    default_ttl: int = _DEFAULT_TTL,
) -> StateStore | _NoOpStore:
    """Connect to Redis and return a StateStore; returns _NoOpStore on failure."""
    store = StateStore(host=host, port=port, default_ttl=default_ttl)
    if store.available:
        return store
    return _NoOpStore()


# -- Pipeline state helpers --------------------------------------------------


def save_stage(
    store: StateStore | _NoOpStore,
    run_id: str,
    stage: str,
    output: dict[str, Any],
) -> None:
    """Persist a single pipeline stage result."""
    store.set(f"pipeline:{run_id}:stage:{stage}", output)


def load_stage(
    store: StateStore | _NoOpStore,
    run_id: str,
    stage: str,
) -> dict[str, Any] | None:
    """Load a previously persisted stage result."""
    return store.get(f"pipeline:{run_id}:stage:{stage}")


def save_result(
    store: StateStore | _NoOpStore,
    run_id: str,
    result: dict[str, Any],
) -> None:
    """Persist the final pipeline result."""
    store.set(f"pipeline:{run_id}:result", result)


def load_result(
    store: StateStore | _NoOpStore,
    run_id: str,
) -> dict[str, Any] | None:
    """Load a previously persisted pipeline result."""
    return store.get(f"pipeline:{run_id}:result")


def list_runs(
    store: StateStore | _NoOpStore,
    prefix: str = "pipeline:",
) -> list[str]:
    """List known pipeline run IDs."""
    keys = store.keys(f"{prefix}*:result")
    run_ids: list[str] = []
    for key in keys:
        parts = key.split(":")
        if len(parts) >= 3:
            run_ids.append(parts[1])
    return sorted(set(run_ids))
