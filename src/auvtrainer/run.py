#!/usr/bin/env python3
"""
AUVTrainer run script.

Starts multiple subprocesses (DB server + controls + simulation) reliably:
- Uses Popen for long-running processes
- Waits for the DB server to become healthy before starting dependents
- Gracefully shuts down all children on Ctrl+C or failure
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

from auvtrainer import __version__


@dataclass(frozen=True)
class ProcSpec:
    """Subprocess specification."""
    name: str
    cmd: list[str]
    cwd: Optional[str] = None
    env: Optional[dict[str, str]] = None


def _project_env() -> dict[str, str]:
    """
    Build an env for subprocesses.

    Ensures unbuffered output so logs appear immediately.
    """
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _popen(spec: ProcSpec) -> subprocess.Popen:
    """
    Start a subprocess (non-blocking).

    \param spec ProcSpec describing the process.
    \return subprocess.Popen handle.
    """
    env = _project_env()
    if spec.env:
        env.update(spec.env)

    # Inherit stdout/stderr so you can see logs in your terminal.
    return subprocess.Popen(
        spec.cmd,
        cwd=spec.cwd,
        env=env,
    )


def _http_ok(url: str, timeout_s: float = 1.5) -> bool:
    """
    Check if an HTTP endpoint responds successfully.

    \param url URL to check.
    \param timeout_s Timeout in seconds.
    \return True if reachable and returns 2xx/3xx, else False.
    """
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _wait_for_http(url: str, deadline_s: float = 20.0, poll_s: float = 0.25) -> None:
    """
    Wait for an HTTP endpoint to become reachable.

    \param url Health endpoint.
    \param deadline_s Max time to wait.
    \param poll_s Poll interval.
    \throws RuntimeError if deadline expires.
    """
    start = time.time()
    while time.time() - start < deadline_s:
        if _http_ok(url):
            return
        time.sleep(poll_s)
    raise RuntimeError(f"Timed out waiting for {url}")


def _terminate_process(proc: subprocess.Popen, name: str, grace_s: float = 6.0) -> None:
    """
    Terminate a process gracefully, then force kill if needed.

    \param proc Process handle.
    \param name Friendly process name for logs.
    \param grace_s Seconds to wait before killing.
    """
    if proc.poll() is not None:
        return

    try:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
    except Exception:
        pass

    start = time.time()
    while time.time() - start < grace_s:
        if proc.poll() is not None:
            return
        time.sleep(0.1)

    try:
        proc.kill()
    except Exception:
        pass


def _run_manual_db() -> int:
    """
    Run the manual_db simulation mode.

    Starts:
    - uvicorn DB server
    - keyboard input
    - manual_database simulation

    \return Exit code.
    """
    procs: list[tuple[str, subprocess.Popen]] = []

    # 1) Start DB server (background)
    db_spec = ProcSpec(
        name="db",
        cmd=[
            "uvicorn",
            "auvtrainer.db.app:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
    )
    db_proc = _popen(db_spec)
    procs.append((db_spec.name, db_proc))

    # 2) Wait until DB is actually ready
    # Adjust this if your router prefix differs (e.g., /db/status).
    health_url = "http://127.0.0.1:8000/db/status"
    try:
        _wait_for_http(health_url, deadline_s=30.0)
    except Exception as e:
        print(f"[runner] DB failed to become healthy: {e}", file=sys.stderr)
        # Print a hint if uvicorn died immediately
        if db_proc.poll() is not None:
            print("[runner] DB process exited early.", file=sys.stderr)
        for name, p in reversed(procs):
            _terminate_process(p, name)
        return 1

    # 3) Start other processes (background)
    kb_spec = ProcSpec(
        name="controls",
        cmd=[sys.executable, "-m", "auvtrainer.controls.keyboard_input"],
    )
    kb_proc = _popen(kb_spec)
    procs.append((kb_spec.name, kb_proc))

    sim_spec = ProcSpec(
        name="simulation",
        cmd=[sys.executable, "-m", "auvtrainer.simulation.manual_database"],
    )
    sim_proc = _popen(sim_spec)
    procs.append((sim_spec.name, sim_proc))

    # 4) Monitor: if any child exits, shut down the rest.
    try:
        while True:
            for name, p in procs:
                code = p.poll()
                if code is not None:
                    print(f"[runner] Process '{name}' exited with code {code}")
                    # stop others
                    for n2, p2 in reversed(procs):
                        if p2 is not p:
                            _terminate_process(p2, n2)
                    return int(code) if isinstance(code, int) else 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n[runner] Ctrl+C received; shutting down...")
        for name, p in reversed(procs):
            _terminate_process(p, name)
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="AUVTrainer runner")
    parser.add_argument("--version", action="version", version=f"AUVTrainer {__version__}")
    parser.add_argument("--simulation_type", type=str, choices=["manual_db"], help="Type of simulation to run")

    args = parser.parse_args()

    if args.simulation_type == "manual_db":
        raise SystemExit(_run_manual_db())

    print("Please specify a valid simulation type. Use --help for more information.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
