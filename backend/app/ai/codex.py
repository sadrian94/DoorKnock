"""Codex App Server adapter using Codex-managed ChatGPT authentication."""

import asyncio
import json
import os
import queue
import shutil
import subprocess
import threading
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from typing import Any, Optional


class CodexError(Exception):
    pass


class CodexAppServer:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.pending: dict[int, Future] = {}
        self.events: queue.Queue[dict[str, Any]] = queue.Queue()
        self.next_id = 0
        self.start_lock = threading.RLock()
        self.request_lock = threading.Lock()
        self.generation_lock = asyncio.Lock()

    async def start(self) -> None:
        await asyncio.to_thread(self._start_sync)

    def _start_sync(self) -> None:
        with self.start_lock:
            if self.process and self.process.poll() is None:
                return
            executable = shutil.which("codex")
            if not executable:
                raise CodexError("Codex CLI is not installed or not on the server PATH")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.process = subprocess.Popen(
                [executable, "app-server", "--stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            threading.Thread(target=self._read_messages, daemon=True).start()
            self._call_started_sync("initialize", {
                "clientInfo": {"name": "doorknock", "title": "DoorKnock", "version": "0.1.0"}
            })
            self._send({"method": "initialized", "params": {}})

    def _send(self, message: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise CodexError("Codex App Server is unavailable")
        self.process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def _read_messages(self) -> None:
        process = self.process
        assert process and process.stdout
        while line := process.stdout.readline():
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "id" in message:
                with self.request_lock:
                    future = self.pending.pop(message["id"], None)
                if future and not future.done():
                    if "error" in message:
                        future.set_exception(CodexError(message["error"].get("message", "Codex request failed")))
                    else:
                        future.set_result(message.get("result", {}))
            elif "method" in message:
                self.events.put(message)
        with self.request_lock:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(CodexError("Codex App Server stopped"))
            self.pending.clear()

    def _call_started_sync(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self.request_lock:
            self.next_id += 1
            request_id = self.next_id
            future: Future = Future()
            self.pending[request_id] = future
        self._send({"method": method, "id": request_id, "params": params})
        try:
            return future.result(timeout=30)
        except FutureTimeoutError as exc:
            raise CodexError(f"Codex App Server timed out during {method}") from exc
        finally:
            with self.request_lock:
                self.pending.pop(request_id, None)

    async def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        await self.start()
        return await asyncio.to_thread(self._call_started_sync, method, params)

    async def close(self) -> None:
        await asyncio.to_thread(self._close_sync)

    def _close_sync(self) -> None:
        with self.start_lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process = None

    async def status(self) -> dict[str, Any]:
        data = await self.call("account/read", {"refreshToken": False})
        account = data.get("account") or {}
        return {"connected": account.get("type") == "chatgpt", "auth_type": account.get("type")}

    async def start_login(self) -> dict[str, Any]:
        return await self.call("account/login/start", {"type": "chatgpt", "useHostedLoginSuccessPage": True, "appBrand": "codex"})

    async def generate_json(self, prompt: str, system_instruction: Optional[str], model: Optional[str]) -> dict[str, Any]:
        async with self.generation_lock:
            if not (await self.status())["connected"]:
                raise CodexError("Connect Codex with ChatGPT in Settings first")
            thread_params: dict[str, Any] = {"sandbox": "read-only", "approvalPolicy": "never"}
            if model:
                thread_params["model"] = model
            thread = await self.call("thread/start", thread_params)
            thread_id = thread["thread"]["id"]
            instruction = (system_instruction or "") + "\nReturn only a valid JSON object. Do not use tools or access local files."
            turn = await self.call("turn/start", {
                "threadId": thread_id,
                "input": [{"type": "text", "text": instruction + "\n\n" + prompt}],
                "sandboxPolicy": {"type": "readOnly"},
                "approvalPolicy": "never",
            })
            turn_id = turn["turn"]["id"]
            answer = ""
            try:
                async with asyncio.timeout(180):
                    while True:
                        event = await asyncio.to_thread(self.events.get)
                        params = event.get("params") or {}
                        if event.get("method") == "item/completed" and params.get("threadId") == thread_id:
                            item = params.get("item") or {}
                            if item.get("type") == "agentMessage":
                                answer = item.get("text", answer)
                        if event.get("method") == "turn/completed" and params.get("turn", {}).get("id") == turn_id:
                            if params["turn"].get("status") != "completed":
                                raise CodexError("Codex generation did not complete")
                            break
            except TimeoutError as exc:
                raise CodexError("Codex generation timed out") from exc
            try:
                result = json.loads(answer)
                if not isinstance(result, dict):
                    raise ValueError("Expected object")
                return result
            except ValueError as exc:
                raise CodexError("Codex returned invalid JSON") from exc


app_server = CodexAppServer()


class CodexClient:
    def __init__(self, model: Optional[str] = None):
        self.model = model

    def is_configured(self) -> bool:
        return shutil.which("codex") is not None

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> dict[str, Any]:
        return await app_server.generate_json(prompt, system_instruction, self.model)
