from __future__ import annotations

import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib import error as urllib_error, request as urllib_request

BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'
LOG_DIR = BASE_DIR / 'logs'
STATE_FILE = LOG_DIR / 'stack_state.json'
STACK_LOG = LOG_DIR / 'stack_manager.log'


@dataclass
class ServiceConfig:
    name: str
    command: List[str]
    cwd: Path
    log_file: Path
    host: str = '127.0.0.1'
    port: Optional[int] = None
    retries: int = 3
    retry_delay: float = 3.0
    ready_timeout: float = 25.0
    env: Optional[Dict[str, str]] = None
    healthcheck_path: Optional[str] = None


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def _log(message: str) -> None:
    line = f"[{_timestamp()}] {message}"
    print(line)
    STACK_LOG.parent.mkdir(exist_ok=True)
    with STACK_LOG.open('a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    system = platform.system()
    try:
        if system == 'Windows':
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except OSError:
        return False


def _force_kill(pid: int) -> None:
    system = platform.system()
    if system == 'Windows':
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGKILL)


def _wait_for_port(host: str, port: int, timeout: float) -> bool:
    if port is None:
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def _check_health(service: ServiceConfig) -> bool:
    if not service.port or not service.healthcheck_path:
        return True

    url = f"http://{service.host}:{service.port}{service.healthcheck_path}"
    deadline = time.time() + service.ready_timeout
    while time.time() < deadline:
        try:
            with urllib_request.urlopen(url, timeout=5) as response:
                if response.status < 500:
                    return True
        except urllib_error.URLError:
            time.sleep(1)
            continue
    return False


def _terminate_pid(pid: int, name: str) -> None:
    if not _pid_is_running(pid):
        _log(f"{name}: process {pid} already stopped")
        return

    system = platform.system()
    try:
        if system == 'Windows':
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        _log(f"{name}: process {pid} unavailable during stop")
        return

    for _ in range(10):
        if not _pid_is_running(pid):
            _log(f"{name}: process {pid} stopped cleanly")
            return
        time.sleep(1)

    _log(f"{name}: escalating termination for pid {pid}")
    _force_kill(pid)

    for _ in range(5):
        if not _pid_is_running(pid):
            _log(f"{name}: process {pid} force-killed")
            return
        time.sleep(0.5)

    _log(f"{name}: WARNING pid {pid} still running after force kill")


def _detect_backend_python() -> str:
    candidates: List[Path] = []
    if platform.system() == 'Windows':
        candidates.append(BACKEND_DIR / '.venv' / 'Scripts' / 'python.exe')
    else:
        candidates.append(BACKEND_DIR / '.venv' / 'bin' / 'python')

    if sys.executable:
        candidates.append(Path(sys.executable))

    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)
    return 'python'


def _detect_npm_command() -> str:
    return 'npm.cmd' if platform.system() == 'Windows' else 'npm'


def _build_services() -> List[ServiceConfig]:
    python_exe = _detect_backend_python()
    npm_cmd = _detect_npm_command()

    backend_env = os.environ.copy()
    backend_env.setdefault('PYTHONPATH', str(BACKEND_DIR))

    backend = ServiceConfig(
        name='backend',
        command=[python_exe, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8100'],
        cwd=BACKEND_DIR,
        log_file=LOG_DIR / 'backend.log',
        host='127.0.0.1',
        port=8100,
        retries=3,
        retry_delay=4.0,
        ready_timeout=25.0,
        env=backend_env,
        healthcheck_path='/health',
    )

    frontend_env = os.environ.copy()
    frontend_env.setdefault('BROWSER', 'none')

    frontend = ServiceConfig(
        name='frontend',
        command=[npm_cmd, 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '5174'],
        cwd=FRONTEND_DIR,
        log_file=LOG_DIR / 'frontend.log',
        host='127.0.0.1',
        port=5174,
        retries=3,
        retry_delay=5.0,
        ready_timeout=35.0,
        env=frontend_env,
    )

    return [backend, frontend]


def _start_service(service: ServiceConfig, creationflags: int) -> subprocess.Popen:
    service.log_file.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, service.retries + 1):
        with service.log_file.open('a', encoding='utf-8') as log_handle:
            log_handle.write('\n' + '=' * 80 + '\n')
            log_handle.write(f"{_timestamp()} Starting {service.name} attempt {attempt}\n")
            log_handle.write('=' * 80 + '\n')
            log_handle.flush()

            env = os.environ.copy()
            if service.env:
                env.update(service.env)

            try:
                process = subprocess.Popen(
                    service.command,
                    cwd=str(service.cwd),
                    stdout=log_handle,
                    stderr=log_handle,
                    env=env,
                    creationflags=creationflags,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(f"Failed to start {service.name}: {exc}") from exc

        if service.port:
            if _wait_for_port(service.host, service.port, service.ready_timeout):
                time.sleep(0.5)
                if process.poll() is None:
                    if service.healthcheck_path and not _check_health(service):
                        _log(f"{service.name}: health check failed, retrying")
                    else:
                        _log(f"{service.name}: listening on {service.host}:{service.port} (pid {process.pid})")
                        return process
                else:
                    _log(f"{service.name}: detected crash after binding, retrying")
        else:
            time.sleep(service.retry_delay)
            if process.poll() is None:
                _log(f"{service.name}: started (pid {process.pid})")
                return process

        _log(f"{service.name}: start attempt {attempt} failed, retrying")
        _terminate_pid(process.pid, service.name)

    raise RuntimeError(f"{service.name}: exceeded retry limit")


def _load_state() -> Optional[Dict[str, object]]:
    if not STATE_FILE.exists():
        return None
    try:
        with STATE_FILE.open('r', encoding='utf-8') as fh:
            return json.load(fh)
    except json.JSONDecodeError:
        return None


def _write_state(services: List[Dict[str, object]]) -> None:
    data = {
        'created_at': _timestamp(),
        'services': services,
    }
    with STATE_FILE.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)


def start_stack() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    existing = _load_state()
    if existing:
        running = [svc for svc in existing.get('services', []) if _pid_is_running(svc.get('pid', -1))]
        if running:
            details = ', '.join(f"{svc['name']} (pid {svc['pid']})" for svc in running)
            _log(f"Stack appears to be running: {details}. Stop it before starting again.")
            raise SystemExit(1)
        else:
            STATE_FILE.unlink(missing_ok=True)

    services = _build_services()
    creationflags = 0
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    started: List[Dict[str, object]] = []
    processes: List[subprocess.Popen] = []

    try:
        for service in services:
            process = _start_service(service, creationflags)
            processes.append(process)
            started.append(
                {
                    'name': service.name,
                    'pid': process.pid,
                    'command': service.command,
                    'log_file': str(service.log_file),
                    'cwd': str(service.cwd),
                }
            )
    except Exception as exc:
        _log(f"Error starting services: {exc}")
        for proc, svc in zip(processes, services):
            _terminate_pid(proc.pid, svc.name)
        raise SystemExit(1) from exc

    _write_state(started)
    summary = ', '.join(f"{svc['name']} (pid {svc['pid']})" for svc in started)
    _log(f"All services started successfully: {summary}")
    _log(f"Logs written to {LOG_DIR}")


def stop_stack() -> None:
    state = _load_state()
    if not state:
        _log('Stack state not found. Nothing to stop.')
        return

    services = state.get('services', [])
    if not services:
        _log('Stack state empty. Nothing to stop.')
        STATE_FILE.unlink(missing_ok=True)
        return

    # Stop in reverse order to unwind dependencies
    for svc in reversed(services):
        pid = svc.get('pid')
        name = svc.get('name', 'unknown')
        if pid is None:
            continue
        _terminate_pid(int(pid), name)

    STATE_FILE.unlink(missing_ok=True)
    _log('All services stopped and state cleared.')


if __name__ == '__main__':
    start_stack()
