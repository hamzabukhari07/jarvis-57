"""
System Monitor — background metric checks with voice alert support.
Zero subprocess calls on all platforms — uses ctypes/pynvml/psutil/wmi only.
"""
import ctypes
import platform
import time

import psutil

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

DEFAULT_THRESHOLDS = {
    "cpu":  90.0,
    "ram":  90.0,
    "temp": 85.0,
    "gpu":  95.0,
}

_COOLDOWN   = 300   # seconds between same-type alerts (5 min)
_CPU_STREAK = 3     # consecutive high readings required before CPU alert

# ── NVML DLL cache (Windows: nvml.dll, Linux: libnvidia-ml.so.1) ─────────────
_nvml_lib: object = None
_nvml_ok:  object = None   # None=untested  True=works  False=unavailable


def _nvml_gpu() -> float:
    """GPU utilisation via NVML — zero subprocess on all platforms."""
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0
    try:
        class _Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            if _OS == "Windows":
                candidates = ("nvml", r"C:\Windows\System32\nvml.dll")
                _load = ctypes.WinDLL
            else:
                candidates = (
                    "libnvidia-ml.so.1",
                    "libnvidia-ml.so",
                    "libnvidia-ml.dylib",
                )
                _load = ctypes.CDLL
            for name in candidates:
                try:
                    lib = _load(name)
                    lib.nvmlInit_v2()
                    _nvml_lib = lib
                    break
                except Exception:
                    continue

        if _nvml_lib is None:
            _nvml_ok = False
            return -1.0

        dev = ctypes.c_void_p()
        _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        u = _Util()
        _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))
        _nvml_ok = True
        return float(u.gpu)
    except Exception:
        _nvml_ok = False
        return -1.0


# ── Windows PDH GPU Performance Tracker (AMD Radeon, Intel, NVIDIA) ────────
class _WindowsPDH_GPU:
    def __init__(self):
        self.ok = False
        if _OS != "Windows":
            return
        try:
            from ctypes import wintypes
            self.pdh = ctypes.windll.pdh
            self.hQuery = wintypes.HANDLE()
            self.hCounter = wintypes.HANDLE()
            if self.pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.hQuery)) == 0:
                # 3D engine is standard for active GPU usage across AMD, Intel, NVIDIA
                res = self.pdh.PdhAddEnglishCounterW(self.hQuery, r"\GPU Engine(*engtype_3D)\Utilization Percentage", 0, ctypes.byref(self.hCounter))
                if res != 0:
                    res = self.pdh.PdhAddEnglishCounterW(self.hQuery, r"\GPU Engine(*)\Utilization Percentage", 0, ctypes.byref(self.hCounter))
                if res == 0:
                    self.pdh.PdhCollectQueryData(self.hQuery)
                    self.ok = True
        except Exception:
            self.ok = False

    def read(self) -> float:
        if not self.ok:
            return -1.0
        try:
            from ctypes import wintypes
            class PDH_FMT_COUNTERVALUE(ctypes.Structure):
                _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]
            self.pdh.PdhCollectQueryData(self.hQuery)
            val = PDH_FMT_COUNTERVALUE()
            res = self.pdh.PdhGetFormattedCounterValue(self.hCounter, 0x00000200, None, ctypes.byref(val))
            if res == 0 and val.CStatus == 0:
                return max(0.0, min(100.0, round(val.doubleValue, 1)))
        except Exception:
            pass
        return 0.0

_pdh_gpu_tracker: _WindowsPDH_GPU | None = None

_nvml_py = None            # cached pynvml module, initialised once
_nvml_py_handle = None
_nvml_py_failed = False


def _get_gpu_usage() -> float:
    global _pdh_gpu_tracker, _nvml_py, _nvml_py_handle, _nvml_py_failed
    # nvmlInit()/nvmlDeviceGetHandleByIndex() are not free and this runs on the
    # UI's 500 ms telemetry tick. Initialise the binding once, then reuse it.
    if not _nvml_py_failed:
        try:
            if _nvml_py is None:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=FutureWarning)
                    import pynvml  # type: ignore
                pynvml.nvmlInit()
                _nvml_py = pynvml
                _nvml_py_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            return float(_nvml_py.nvmlDeviceGetUtilizationRates(_nvml_py_handle).gpu)
        except Exception:
            _nvml_py_failed = True

    # 2. nvml.dll fallback (NVIDIA)
    nvml_val = _nvml_gpu()
    if nvml_val >= 0:
        return nvml_val

    # 3. Windows Native Performance Data Helper (AMD Radeon RX series, Intel Arc/Iris, NVIDIA)
    if _OS == "Windows":
        if _pdh_gpu_tracker is None:
            _pdh_gpu_tracker = _WindowsPDH_GPU()
        val = _pdh_gpu_tracker.read()
        if val >= 0:
            return val

    return -1.0


_cpu_temp_cache = (0.0, -1.0)     # (monotonic timestamp, value)
_CPU_TEMP_TTL   = 60.0            # seconds between real reads


def _get_cpu_temp() -> float:
    global _cpu_temp_cache
    # The Windows WMI thermal-zone query below is very slow (measured 30-160 ms,
    # occasionally ~0.5 s) and it is the only option on Windows — psutil has no
    # sensors_temperatures() there. Cache it for a minute so neither the 10 s
    # system monitor nor the on-demand status tool pays that cost every call.
    now = time.monotonic()
    cached_at, cached_val = _cpu_temp_cache
    if now - cached_at < _CPU_TEMP_TTL:
        return cached_val

    result = -1.0

    # psutil — works on Linux; occasionally Windows with proper drivers
    try:
        temps = psutil.sensors_temperatures()
        for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                     "cpu-thermal", "zenpower", "it8688"]:
            if name in temps and temps[name]:
                result = temps[name][0].current
                break
        else:
            for entries in temps.values():
                if entries:
                    result = entries[0].current
                    break
    except Exception:
        pass

    # Windows: wmi module (pure Python COM, zero subprocess)
    if result < 0 and _OS == "Windows":
        try:
            import wmi  # type: ignore
            w = wmi.WMI(namespace="root/wmi")
            tz = w.MSAcpi_ThermalZoneTemperature()
            if tz:
                result = (tz[0].CurrentTemperature / 10.0) - 273.15
        except Exception:
            pass

    _cpu_temp_cache = (now, result)
    return result


def get_system_status() -> dict:
    """Snapshot of current system metrics for the system_status tool."""
    cpu  = psutil.cpu_percent(interval=0.2)
    ram  = psutil.virtual_memory()
    temp = _get_cpu_temp()
    gpu  = _get_gpu_usage()

    boot_time   = psutil.boot_time()
    uptime_secs = time.time() - boot_time
    uptime_h    = int(uptime_secs // 3600)
    uptime_m    = int((uptime_secs % 3600) // 60)

    battery_info = "Desktop PC (Direct AC power, no battery)"
    try:
        b = psutil.sensors_battery()
        if b is not None:
            plugged_str = "Plugged in" if b.power_plugged else "On battery"
            battery_info = f"{round(b.percent, 1)}% ({plugged_str})"
    except Exception:
        battery_info = "Not available"

    return {
        "cpu_percent":   round(cpu, 1),
        "ram_percent":   round(ram.percent, 1),
        "ram_used_gb":   round(ram.used   / 1024 ** 3, 1),
        "ram_total_gb":  round(ram.total  / 1024 ** 3, 1),
        "cpu_temp_c":    round(temp, 1) if temp > 0 else None,
        "gpu_percent":   round(gpu,  1) if gpu  >= 0 else None,
        "battery":       battery_info,
        "uptime":        f"{uptime_h}h {uptime_m}m",
        "process_count": len(psutil.pids()),
    }


class SystemMonitor:
    """
    Stateful monitor — cooldown state persists across session reconnections.
    Call check() periodically; returns a [SYSTEM_ALERT] string or None.
    """

    def __init__(self, thresholds: dict | None = None):
        self.thresholds   = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._last_alert: dict[str, float] = {}
        self._cpu_streak  = 0

    def _can_alert(self, key: str) -> bool:
        return (time.monotonic() - self._last_alert.get(key, 0)) > _COOLDOWN

    def _record(self, key: str):
        self._last_alert[key] = time.monotonic()

    def check(self) -> str | None:
        try:
            try:
                from ui import _metrics
                snap = _metrics.snapshot()
                cpu = snap.get("cpu", 0.0)
                ram = snap.get("mem", 0.0)
                temp = snap.get("tmp", -1.0)
                gpu = snap.get("gpu", -1.0)
            except Exception:
                cpu  = psutil.cpu_percent(interval=0.1)
                ram  = psutil.virtual_memory().percent
                temp = _get_cpu_temp()
                gpu  = _get_gpu_usage()
        except Exception:
            return None

        alerts: list[str] = []

        # Check active coding agent tasks and their CPU contribution
        task_cpu = 0.0
        has_running_tasks = False
        try:
            from core.task_manager import get_task_manager
            mgr = get_task_manager()
            task_cpu = mgr.get_active_tasks_cpu_percent()
            has_running_tasks = len(mgr.list_running_tasks()) > 0
        except Exception:
            pass

        # If background tasks are running or task subprocesses account for >= 50% of the CPU spike, suppress alert (known build/AI workload)
        is_task_driven = has_running_tasks or (task_cpu > 0.0 and task_cpu >= (cpu * 0.5))

        if cpu >= self.thresholds["cpu"]:
            if not is_task_driven:
                self._cpu_streak += 1
                if self._cpu_streak >= _CPU_STREAK and self._can_alert("cpu"):
                    alerts.append(
                        f"[SYSTEM_ALERT] CPU usage has been critically high ({cpu:.0f}%) "
                        "for several seconds. Warn the user in their language and suggest "
                        "closing heavy applications."
                    )
                    self._record("cpu")
                    self._cpu_streak = 0
            else:
                self._cpu_streak = 0
        else:
            self._cpu_streak = 0

        if ram >= self.thresholds["ram"] and self._can_alert("ram"):
            alerts.append(
                f"[SYSTEM_ALERT] RAM is at {ram:.0f}% — nearly exhausted. "
                "Warn the user in their language and suggest freeing memory."
            )
            self._record("ram")

        if temp > 0 and temp >= self.thresholds["temp"] and self._can_alert("temp"):
            alerts.append(
                f"[SYSTEM_ALERT] CPU temperature is {temp:.0f}°C — above the safe limit. "
                "Warn the user in their language and advise reducing system load "
                "or checking cooling."
            )
            self._record("temp")

        if gpu >= 0 and gpu >= self.thresholds["gpu"] and self._can_alert("gpu"):
            alerts.append(
                f"[SYSTEM_ALERT] GPU load is at {gpu:.0f}%. "
                "Briefly inform the user in their language."
            )
            self._record("gpu")

        return " ".join(alerts) if alerts else None


def system_status_action(parameters: dict, **kwargs) -> str:
    """Action handler for real-time system metrics."""
    return str(get_system_status())


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "system_status",
    "description": (
        "Returns real-time system metrics: CPU usage, RAM, GPU load, CPU temperature, "
        "uptime, and process count. Use when the user asks about computer performance, "
        "temperature, memory, or resource usage."
    ),
    "risk": "read_only",
    "enabled": True,
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    },
    "handler": system_status_action,
}
