#!/usr/bin/env python3
"""
AUVTrainer Runner

Starts and supervises a set of subprocess modules (DB server, controls,
simulations, etc.) with minimal coupling.

How to add a new module:
- Add a ProcSpec to a pipeline in PIPELINES.
- Optionally add a WaitSpec (sleep or http) to gate startup.
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
class WaitSpec:
    """
    Readiness check definition.

    Supported kinds:
    - sleep: wait a fixed number of seconds
    - http: poll an HTTP endpoint until it responds 2xx/3xx

    @param kind Readiness check kind ("sleep" or "http").
    @param target Seconds for sleep, URL for http.
    @param deadline_s Max time to wait for readiness (http only).
    @param poll_s Poll interval (http only).
    """

    kind: str
    target: str
    deadline_s: float = 30.0
    poll_s: float = 0.25


@dataclass(frozen=True)
class ProcSpec:
    """
    Subprocess specification.

    @param name Display name for logs.
    @param cmd argv list.
    @param cwd Optional working directory.
    @param env Optional environment overrides.
    @param wait Optional readiness check to run after starting.
    """

    name: str
    cmd: list[str]
    cwd: Optional[str] = None
    env: Optional[dict[str, str]] = None
    wait: Optional[WaitSpec] = None


@dataclass(frozen=True)
class PipelineSpec:
    """
    Pipeline specification (ordered list of ProcSpec steps).

    @param name Pipeline identifier (matches CLI choice).
    @param steps Ordered list of ProcSpec steps.
    @param primary Optional main process name (informational).
    """

    name: str
    steps: list[ProcSpec]
    primary: Optional[str] = None


def _project_env() -> dict[str, str]:
    """
    Build an environment for subprocesses.

    Ensures unbuffered output so logs appear immediately.

    @return Environment dictionary.
    """
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _popen(spec: ProcSpec) -> subprocess.Popen:
    """
    Start a subprocess (non-blocking).

    @param spec ProcSpec describing the process.
    @return subprocess.Popen handle.
    """
    env = _project_env()
    if spec.env:
        env.update(spec.env)

    return subprocess.Popen(
        spec.cmd,
        cwd=spec.cwd,
        env=env,
    )


def _http_ok(url: str, timeout_s: float = 1.5) -> bool:
    """
    Check whether an HTTP endpoint responds successfully (2xx/3xx).

    @param url URL to check.
    @param timeout_s Timeout in seconds.
    @return True if reachable and returns 2xx/3xx, else False.
    """
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _wait_sleep(seconds: float) -> None:
    """
    Sleep for a fixed amount of time.

    @param seconds Duration in seconds.
    """
    time.sleep(seconds)


def _wait_http(url: str, deadline_s: float, poll_s: float) -> None:
    """
    Wait until an HTTP endpoint responds successfully (2xx/3xx).

    @param url Health endpoint URL.
    @param deadline_s Max time to wait.
    @param poll_s Poll interval.
    @throws RuntimeError if deadline expires.
    """
    start = time.time()
    while (time.time() - start) < deadline_s:
        if _http_ok(url):
            return
        time.sleep(poll_s)
    raise RuntimeError(f"Timed out waiting for HTTP readiness: {url}")


def _apply_wait(wait: WaitSpec) -> None:
    """
    Apply a readiness check.

    @param wait WaitSpec describing the readiness check.
    @throws ValueError if wait.kind is unknown.
    """
    if wait.kind == "sleep":
        _wait_sleep(float(wait.target))
        return

    if wait.kind == "http":
        _wait_http(wait.target, wait.deadline_s, wait.poll_s)
        return

    raise ValueError("Unknown wait kind: %s (supported: sleep, http)" % wait.kind)


def _terminate_process(proc: subprocess.Popen, name: str, grace_s: float = 6.0) -> None:
    """
    Terminate a process gracefully, then force kill if needed.

    @param proc Process handle.
    @param name Friendly process name for logs.
    @param grace_s Seconds to wait before killing.
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
    while (time.time() - start) < grace_s:
        if proc.poll() is not None:
            return
        time.sleep(0.1)

    try:
        proc.kill()
    except Exception:
        pass


def _shutdown_all(procs: list[tuple[str, subprocess.Popen]]) -> None:
    """
    Shut down processes in reverse start order.

    @param procs List of (name, process) tuples.
    """
    for name, p in reversed(procs):
        _terminate_process(p, name)


def run_pipeline(pipeline: PipelineSpec) -> int:
    """
    Start and supervise a pipeline.

    - Starts each step in order
    - Runs optional readiness checks per step
    - If any process exits, shuts down the rest

    @param pipeline PipelineSpec to run.
    @return Exit code.
    """
    procs: list[tuple[str, subprocess.Popen]] = []

    try:
        for step in pipeline.steps:
            p = _popen(step)
            procs.append((step.name, p))

            if step.wait is not None:
                if p.poll() is not None:
                    raise RuntimeError(
                        "Process '%s' exited early with code %s" % (step.name, p.returncode)
                    )
                _apply_wait(step.wait)

        while True:
            for name, p in procs:
                code = p.poll()
                if code is not None:
                    print("[runner] Process '%s' exited with code %s" % (name, code))
                    _shutdown_all([(n, pp) for (n, pp) in procs if pp is not p])
                    return int(code) if isinstance(code, int) else 1
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n[runner] Ctrl+C received; shutting down...")
        _shutdown_all(procs)
        return 0
    except Exception as e:
        print("[runner] Error: %s" % e, file=sys.stderr)
        _shutdown_all(procs)
        return 1


PIPELINES: dict[str, PipelineSpec] = {
    "manual_keyboard": PipelineSpec(
        name="manual_keyboard",
        steps=[
            ProcSpec(
                name="db",
                cmd=[
                    "uvicorn",
                    "auvtrainer.db.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                wait=WaitSpec(
                    kind="http",
                    target="http://127.0.0.1:8000/db/status",
                    deadline_s=30.0,
                    poll_s=0.25,
                ),
            ),
            ProcSpec(
                name="controls",
                cmd=[sys.executable, "-m", "auvtrainer.controls.keyboard"],
                wait=WaitSpec(kind="sleep", target="3"),
            ),
            ProcSpec(
                name="converter",
                cmd=[sys.executable, "-m", "auvtrainer.controls.converter"],
                wait=WaitSpec(kind="sleep", target="3"),
            ),
            ProcSpec(
                name="simulation",
                cmd=[sys.executable, "-m", "auvtrainer.simulation.manual_database"],
            ),
        ],
        primary="simulation",
    ),
}


def main() -> None:
    """
    CLI entrypoint.

    @return None.
    """
    parser = argparse.ArgumentParser(description="AUVTrainer runner")
    parser.add_argument("--version", action="version", version="AUVTrainer %s" % __version__)
    parser.add_argument(
        "--simulation_type",
        type=str.lower,
        choices=sorted(k.lower() for k in PIPELINES.keys()),
        required=True,
        help="Pipeline/simulation to run",
    )

    args = parser.parse_args()
    pipeline = PIPELINES[args.simulation_type]
    raise SystemExit(run_pipeline(pipeline))


if __name__ == "__main__":
    main()
