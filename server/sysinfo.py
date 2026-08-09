"""系统状态采集（监控面板用）。psutil 提供 CPU/内存/磁盘/网络/负载。"""
import os
import time

import psutil

_start_time = time.time()


def _fmt_bytes(b: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024 or unit == "TB":
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def get_system_stats() -> dict:
    """返回一份系统快照，供前端监控面板展示。"""
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=0.3)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

    net = psutil.net_io_counters()
    boot = psutil.boot_time()
    uptime_sec = int(time.time() - boot)

    days, rem = divmod(uptime_sec, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    uptime_str = f"{days}天 {hours}小时 {mins}分" if days else f"{hours}小时 {mins}分"

    hostname = os.uname().nodename if hasattr(os, "uname") else "unknown"
    # 内核只暴露架构，不暴露精确版本号（避免帮助攻击者匹配已知漏洞）
    arch = os.uname().machine if hasattr(os, "uname") else ""

    return {
        "hostname": hostname,
        "arch": arch,
        "uptime": uptime_str,
        "cpu": {
            "percent": round(cpu_percent, 1),
            "per_core": [round(p, 1) for p in per_cpu],
            "cores": psutil.cpu_count(logical=True),
            "load": [round(x, 2) for x in load],
        },
        "memory": {
            "total": vm.total,
            "used": vm.used,
            "available": vm.available,
            "percent": vm.percent,
        },
        "swap": {
            "total": sm.total,
            "used": sm.used,
            "percent": sm.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        },
        "processes": len(psutil.pids()),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fmt": {
            "mem_total": _fmt_bytes(vm.total),
            "mem_used": _fmt_bytes(vm.used),
            "disk_total": _fmt_bytes(disk.total),
            "disk_used": _fmt_bytes(disk.used),
            "disk_free": _fmt_bytes(disk.free),
            "net_sent": _fmt_bytes(net.bytes_sent),
            "net_recv": _fmt_bytes(net.bytes_recv),
        },
    }
