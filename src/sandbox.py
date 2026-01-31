from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SandboxResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int


class SandboxRunner:
    """Docker-based sandbox runner for unsafe tool execution."""

    def __init__(self) -> None:
        self.enabled = os.getenv("ORCH_TOOL_SANDBOX_ENABLED", "1") == "1"
        self.image = os.getenv("ORCH_SANDBOX_IMAGE", "python:3.12-slim")
        self.timeout_sec = int(os.getenv("ORCH_SANDBOX_TIMEOUT_SEC", "10"))
        self.memory_mb = int(os.getenv("ORCH_SANDBOX_MEMORY_MB", "256"))
        self.cpu = os.getenv("ORCH_SANDBOX_CPU", "0.5")
        self.tool_dir = os.getenv("ORCH_SANDBOX_TOOL_DIR", "sandbox_tools")
        self.docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        if not self.enabled:
            return False
        try:
            completed = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return completed.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def run(self, command: List[str], payload: Dict[str, object]) -> SandboxResult:
        if not self.enabled:
            return SandboxResult(
                status="error",
                stdout="",
                stderr="sandbox_disabled",
                exit_code=1,
            )

        if not self.docker_available:
            return SandboxResult(
                status="error",
                stdout="",
                stderr="docker_unavailable",
                exit_code=1,
            )

        serialized = json.dumps(payload, separators=(",", ":"))
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--pids-limit=64",
            "--cpus",
            str(self.cpu),
            "--memory",
            f"{self.memory_mb}m",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--volume",
            f"{self.tool_dir}:/tools:ro",
            "--workdir",
            "/tools",
            self.image,
            *command,
        ]

        try:
            completed = subprocess.run(
                docker_cmd,
                input=serialized,
                text=True,
                capture_output=True,
                timeout=self.timeout_sec,
                check=False,
            )
            return SandboxResult(
                status="ok" if completed.returncode == 0 else "error",
                stdout=completed.stdout.strip(),
                stderr=completed.stderr.strip(),
                exit_code=completed.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                status="error",
                stdout="",
                stderr="sandbox_timeout",
                exit_code=124,
            )
