import logging
import time
from typing import Dict, Any, List
from app.core.plugins.manager import plugin_manager
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class PluginDiagnostics:
    """Collects and exposes plugin framework metrics and health."""

    def __init__(self):
        self.last_collection = 0

    def collect_metrics(self):
        """Record plugin framework metrics into the observability platform."""
        diags = plugin_manager.get_diagnostics()

        # 1. Platform Metrics
        obs_manager.record_metric("plugins_total_installed", float(diags['total_plugins']))

        active_count = 0
        failed_count = 0
        for pid, info in diags['plugins'].items():
            if info['status'] == "ACTIVE":
                active_count += 1
            elif info['status'] == "FAILED":
                failed_count += 1

        obs_manager.record_metric("plugins_active_count", float(active_count))
        obs_manager.record_metric("plugins_failed_count", float(failed_count))

        self.last_collection = time.time()
        logger.debug(f"[plugins-diag] Metrics collected. Active: {active_count}, Failed: {failed_count}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate a detailed report for the system diagnostics engine."""
        diags = plugin_manager.get_diagnostics()

        # Add loading timeline data if available
        report = {
            "framework_status": "OK",
            "plugin_inventory": diags['plugins'],
            "summary": {
                "total": diags['total_plugins'],
                "active": sum(1 for p in diags['plugins'].values() if p['status'] == "ACTIVE"),
                "failed": sum(1 for p in diags['plugins'].values() if p['status'] == "FAILED")
            }
        }
        return report

# Global Diagnostics Instance
plugin_diagnostics = PluginDiagnostics()
