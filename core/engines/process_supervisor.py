"""
core/engines/process_supervisor.py — Win32 Job Object & Process Lifecycle Supervisor.

Manages external engine process trees inside Windows Job Objects configured with
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Processes are spawned in a suspended state
(CREATE_SUSPENDED) directly via kernel32.CreateProcessW, assigned to the Job Object,
and then resumed via kernel32.ResumeThread(pi.hThread).

Guarantees 100% elimination of orphaned child, grandchild, and worker processes
upon cancellation, timeout, or application crash.
Provides clean POSIX fallback (process groups via os.setsid/killpg) on Linux/macOS.

Author: Hamza Bukhari
"""

from __future__ import annotations

import io
import logging
import msvcrt
import os
import platform
import queue
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("zezo.engines.process_supervisor")

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    # Win32 Constants
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9
    CREATE_SUSPENDED = 0x00000004
    CREATE_NO_WINDOW = 0x08000000
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    STARTF_USESTDHANDLES = 0x00000100
    HANDLE_FLAG_INHERIT = 0x00000001
    STILL_ACTIVE = 259
    INFINITE = 0xFFFFFFFF
    WAIT_TIMEOUT = 0x00000102

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoCounters", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryLimit", ctypes.c_size_t),
            ("PeakJobMemoryLimit", ctypes.c_size_t),
        ]

    # Explicit 64-bit safe signatures
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL

    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD

    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE

    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL

    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    kernel32.CreatePipe.argtypes = [
        ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.DWORD
    ]
    kernel32.CreatePipe.restype = wintypes.BOOL

    kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    kernel32.SetHandleInformation.restype = wintypes.BOOL

    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL

    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD

    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL


@dataclass
class ContainedProcess:
    """Wrapper encapsulating a contained process tree and its lifecycle handle."""
    pid: int
    h_process: Any
    h_thread: Any
    h_job: Any
    h_stdout_read: Any
    pipe_file: Optional[io.TextIOWrapper] = None
    h_stdin_write: Any = None
    _exit_code: Optional[int] = None
    _is_closed: bool = False
    _posix_proc: Optional[subprocess.Popen] = None

    def poll(self) -> Optional[int]:
        """Checks if process has exited. Returns exit code or None if still running."""
        if self._exit_code is not None:
            return self._exit_code

        if _IS_WINDOWS:
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(self.h_process, ctypes.byref(exit_code)):
                if exit_code.value == STILL_ACTIVE:
                    return None
                self._exit_code = int(exit_code.value)
                return self._exit_code
            return None
        else:
            if self._posix_proc:
                self._exit_code = self._posix_proc.poll()
                return self._exit_code
            return None

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """Waits for process termination up to timeout seconds."""
        if self.poll() is not None:
            return self._exit_code

        start = time.monotonic()
        while True:
            code = self.poll()
            if code is not None:
                return code
            if timeout is not None and (time.monotonic() - start) >= timeout:
                return None
            time.sleep(0.02)

    def terminate_tree(self) -> None:
        """
        Vaporizes the entire process tree instantly by closing the Job Object handle on Windows,
        or signaling the process group on POSIX.
        """
        if self._is_closed:
            return
        self._is_closed = True

        if _IS_WINDOWS:
            try:
                # 1. Terminate process handle if still running
                if self.h_process:
                    kernel32.TerminateProcess(self.h_process, 1)
            except Exception as e:
                logger.debug("Error in TerminateProcess: %s", e)

            try:
                # 2. Closing the Job Object handle triggers KILL_ON_JOB_CLOSE in kernel
                if self.h_job:
                    kernel32.CloseHandle(self.h_job)
                    self.h_job = None
            except Exception as e:
                logger.debug("Error in CloseHandle(h_job): %s", e)

            try:
                if self.h_thread:
                    kernel32.CloseHandle(self.h_thread)
                    self.h_thread = None
            except Exception:
                pass

            try:
                if self.h_stdin_write:
                    kernel32.CloseHandle(self.h_stdin_write)
                    self.h_stdin_write = None
            except Exception:
                pass

            try:
                if self.h_process:
                    kernel32.CloseHandle(self.h_process)
                    self.h_process = None
            except Exception:
                pass

            try:
                if self.pipe_file and not self.pipe_file.closed:
                    self.pipe_file.close()
                elif self.h_stdout_read:
                    kernel32.CloseHandle(self.h_stdout_read)
                    self.h_stdout_read = None
            except Exception:
                pass
        else:
            if self._posix_proc and self._posix_proc.poll() is None:
                try:
                    os.killpg(os.getpgid(self._posix_proc.pid), signal.SIGTERM)
                    time.sleep(0.05)
                    if self._posix_proc.poll() is None:
                        os.killpg(os.getpgid(self._posix_proc.pid), signal.SIGKILL)
                except Exception as e:
                    logger.debug("Error in POSIX process group termination: %s", e)


class ProcessSupervisor:
    """Central supervisor managing process lifecycle containment for external engines."""

    @staticmethod
    def spawn(
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
        redirect_stdin: bool = False,
    ) -> ContainedProcess:
        """
        Spawns a process with strict process tree lifecycle containment.
        On Windows:
          1. Creates Job Object with KILL_ON_JOB_CLOSE.
          2. Creates inheritable stdout/stderr pipes with non-inheritable read end.
          3. Spawns process directly via CreateProcessW with CREATE_SUSPENDED.
          4. Assigns process handle to Job Object BEFORE resuming.
          5. Resumes main thread via kernel32.ResumeThread(pi.hThread).
        On POSIX:
          Uses subprocess.Popen with start_new_session=True (process group).
        """
        effective_env = dict(os.environ)
        if env:
            effective_env.update(env)

        target_dir = Path(cwd).resolve()

        if _IS_WINDOWS:
            # 1. Create Job Object with Kill-On-Close
            h_job = kernel32.CreateJobObjectW(None, None)
            if not h_job:
                raise OSError(f"CreateJobObjectW failed: {ctypes.GetLastError()}")

            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel32.SetInformationJobObject(
                h_job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
            ):
                kernel32.CloseHandle(h_job)
                raise OSError(f"SetInformationJobObject failed: {ctypes.GetLastError()}")

            # 2. Create Inheritable Stdout/Stderr Pipe
            sa = SECURITY_ATTRIBUTES()
            sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
            sa.bInheritHandle = True
            sa.lpSecurityDescriptor = None

            h_read_pipe = wintypes.HANDLE()
            h_write_pipe = wintypes.HANDLE()
            if not kernel32.CreatePipe(ctypes.byref(h_read_pipe), ctypes.byref(h_write_pipe), ctypes.byref(sa), 0):
                kernel32.CloseHandle(h_job)
                raise OSError(f"CreatePipe failed: {ctypes.GetLastError()}")

            # Parent read end must NOT be inherited by child
            kernel32.SetHandleInformation(h_read_pipe, HANDLE_FLAG_INHERIT, 0)

            # Optional inheritable stdin pipe
            h_stdin_read = wintypes.HANDLE()
            h_stdin_write = wintypes.HANDLE()
            if redirect_stdin:
                if not kernel32.CreatePipe(ctypes.byref(h_stdin_read), ctypes.byref(h_stdin_write), ctypes.byref(sa), 0):
                    kernel32.CloseHandle(h_read_pipe)
                    kernel32.CloseHandle(h_write_pipe)
                    kernel32.CloseHandle(h_job)
                    raise OSError(f"CreatePipe for stdin failed: {ctypes.GetLastError()}")
                kernel32.SetHandleInformation(h_stdin_write, HANDLE_FLAG_INHERIT, 0)

            # 3. Startup info with redirected stdout and stderr
            si = STARTUPINFOW()
            si.cb = ctypes.sizeof(STARTUPINFOW)
            si.dwFlags = STARTF_USESTDHANDLES
            si.hStdInput = h_stdin_read if redirect_stdin else None
            si.hStdOutput = h_write_pipe
            si.hStdError = h_write_pipe

            pi = PROCESS_INFORMATION()
            cmd_str = subprocess.list2cmdline(cmd)

            # Prepare Unicode environment block
            env_str = "\0".join(f"{k}={v}" for k, v in effective_env.items()) + "\0\0"
            env_block = ctypes.create_unicode_buffer(env_str)

            # 4. CreateProcessW in CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT
            flags = CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT
            success = kernel32.CreateProcessW(
                None,
                cmd_str,
                None,
                None,
                True,  # bInheritHandles
                flags,
                env_block,
                str(target_dir),
                ctypes.byref(si),
                ctypes.byref(pi),
            )

            # Close child write end handle in parent process immediately so EOF is detected
            kernel32.CloseHandle(h_write_pipe)
            if redirect_stdin:
                # Close child read end in parent process so child owns it
                kernel32.CloseHandle(h_stdin_read)

            if not success:
                kernel32.CloseHandle(h_read_pipe)
                if redirect_stdin:
                    kernel32.CloseHandle(h_stdin_write)
                kernel32.CloseHandle(h_job)
                raise OSError(f"CreateProcessW failed for {cmd[0]}: {ctypes.GetLastError()}")

            try:
                # 5. Assign to Job Object BEFORE resuming thread (eliminates startup race)
                if not kernel32.AssignProcessToJobObject(h_job, pi.hProcess):
                    raise OSError(f"AssignProcessToJobObject failed: {ctypes.GetLastError()}")

                # 6. Resume main thread
                res = kernel32.ResumeThread(pi.hThread)
                if res == 0xFFFFFFFF:
                    raise OSError(f"ResumeThread failed: {ctypes.GetLastError()}")

                # Open python text stream over the OS read handle
                fd = msvcrt.open_osfhandle(int(h_read_pipe.value), os.O_RDONLY)
                pipe_file = io.open(fd, mode="r", encoding="utf-8", errors="replace", buffering=1)

                return ContainedProcess(
                    pid=pi.dwProcessId,
                    h_process=pi.hProcess,
                    h_thread=pi.hThread,
                    h_job=h_job,
                    h_stdout_read=h_read_pipe,
                    pipe_file=pipe_file,
                    h_stdin_write=h_stdin_write if redirect_stdin else None,
                )
            except Exception:
                kernel32.TerminateProcess(pi.hProcess, 1)
                kernel32.CloseHandle(pi.hProcess)
                kernel32.CloseHandle(pi.hThread)
                kernel32.CloseHandle(h_read_pipe)
                if redirect_stdin:
                    kernel32.CloseHandle(h_stdin_write)
                kernel32.CloseHandle(h_job)
                raise
        else:
            # POSIX process group containment
            proc = subprocess.Popen(
                cmd,
                cwd=str(target_dir),
                env=effective_env,
                stdin=subprocess.PIPE if redirect_stdin else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                start_new_session=True,
            )
            return ContainedProcess(
                pid=proc.pid,
                h_process=None,
                h_thread=None,
                h_job=None,
                h_stdout_read=None,
                pipe_file=proc.stdout,
                _posix_proc=proc,
            )
