"""System metrics collection for Prometheus.

This module collects system-level metrics (CPU, memory, disk) using psutil.
"""

from app.core.metrics import (
    system_cpu_percent,
    system_memory_bytes,
    system_disk_bytes,
    PSUTIL_AVAILABLE
)
import asyncio
import logging
import platform

logger = logging.getLogger(__name__)


async def collect_system_metrics():
    """Collect system metrics periodically."""
    if not PSUTIL_AVAILABLE:
        logger.warning("System metrics not available (psutil not installed)")
        return
    
    if not system_cpu_percent:
        logger.warning("System metrics not initialized")
        return
    
    try:
        import psutil
        
        # CPU metrics
        cpu_percent_total = psutil.cpu_percent(interval=0.1)
        system_cpu_percent.labels(cpu="total").set(cpu_percent_total)
        
        # Per-core CPU metrics
        cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        for i, percent in enumerate(cpu_percent_per_core):
            system_cpu_percent.labels(cpu=f"core_{i}").set(percent)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        system_memory_bytes.labels(type="total").set(memory.total)
        system_memory_bytes.labels(type="available").set(memory.available)
        system_memory_bytes.labels(type="used").set(memory.used)
        system_memory_bytes.labels(type="free").set(memory.free)
        
        # Disk metrics - get root partition
        if platform.system() == "Windows":
            # Windows: use C: drive
            disk = psutil.disk_usage("C:\\")
            mount = "C:\\"
        else:
            # Unix-like: use root partition
            disk = psutil.disk_usage("/")
            mount = "/"
        
        system_disk_bytes.labels(type="total", mount=mount).set(disk.total)
        system_disk_bytes.labels(type="used", mount=mount).set(disk.used)
        system_disk_bytes.labels(type="free", mount=mount).set(disk.free)
        
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}", exc_info=True)


async def start_system_metrics_collector(interval: int = 60):
    """Start system metrics collection in background.
    
    Args:
        interval: Collection interval in seconds (default: 60)
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("System metrics collector not started (psutil not available)")
        return
    
    logger.info(f"Starting system metrics collector (interval: {interval}s)")
    
    while True:
        try:
            await collect_system_metrics()
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("System metrics collector stopped")
            break
        except Exception as e:
            logger.error(f"Error in system metrics collector: {e}", exc_info=True)
            await asyncio.sleep(interval)
