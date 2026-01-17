"""System metrics collection for Prometheus.

This module collects system-level metrics (CPU, memory, disk) using psutil.
"""

import logging
import platform
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.core.metrics import (
    system_cpu_usage_percent,
    system_memory_bytes,
    system_disk_bytes,
)

logger = logging.getLogger(__name__)


def collect_system_metrics() -> None:
    """Collect and update system metrics.
    
    This function collects:
    - CPU usage (total and per-core)
    - Memory usage (total, available, used, free)
    - Disk usage (total, used, free) per mount point
    
    Should be called periodically (e.g., every 60 seconds).
    """
    if not PSUTIL_AVAILABLE:
        logger.debug("psutil not available, skipping system metrics collection")
        return

    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
        cpu_total = psutil.cpu_percent(interval=None)
        
        # Total CPU usage
        system_cpu_usage_percent.labels(cpu="total").set(cpu_total)
        
        # Per-core CPU usage
        for i, cpu_pct in enumerate(cpu_percent):
            system_cpu_usage_percent.labels(cpu=f"cpu{i}").set(cpu_pct)

        # Memory metrics
        memory = psutil.virtual_memory()
        system_memory_bytes.labels(type="total").set(memory.total)
        system_memory_bytes.labels(type="available").set(memory.available)
        system_memory_bytes.labels(type="used").set(memory.used)
        system_memory_bytes.labels(type="free").set(memory.free)

        # Disk metrics
        disk_partitions = psutil.disk_partitions()
        for partition in disk_partitions:
            try:
                # Skip network filesystems on Windows to avoid slow operations
                if platform.system() == "Windows" and "network" in partition.fstype.lower():
                    continue
                    
                disk_usage = psutil.disk_usage(partition.mountpoint)
                mount = partition.mountpoint.replace("\\", "/")  # Normalize path separators
                
                system_disk_bytes.labels(mount=mount, type="total").set(disk_usage.total)
                system_disk_bytes.labels(mount=mount, type="used").set(disk_usage.used)
                system_disk_bytes.labels(mount=mount, type="free").set(disk_usage.free)
            except PermissionError:
                # Skip partitions we don't have permission to access
                logger.debug(f"Permission denied accessing {partition.mountpoint}")
                continue
            except Exception as e:
                logger.warning(f"Error collecting disk metrics for {partition.mountpoint}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}", exc_info=True)


async def start_system_metrics_collector(interval: int = 60) -> None:
    """Start background task to collect system metrics periodically.
    
    Args:
        interval: Collection interval in seconds (default: 60)
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, system metrics collection disabled")
        return

    import asyncio

    logger.info(f"Starting system metrics collector (interval: {interval}s)")

    while True:
        try:
            collect_system_metrics()
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("System metrics collector cancelled")
            break
        except Exception as e:
            logger.error(f"Error in system metrics collector: {e}", exc_info=True)
            await asyncio.sleep(interval)
