"""
reporter.py
===========
Handles reporting of system expansion, research results, and meta-governor 
telemetry to Supabase.
"""

import os
import logging
from datetime import datetime
try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    create_client = None
    load_dotenv = None

logger = logging.getLogger(__name__)

class SupabaseReporter:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        self.client = None
        
        if create_client and self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                logger.error(f"[SupabaseReporter] Connection failed: {e}")
        else:
            logger.warning("[SupabaseReporter] Supabase not configured. Logging to local only.")

    async def report_expansion(self, cycle_id: str, action: str, analysis: str, meta_commentary: str):
        """Pushes high-level expansion metrics to the Report table."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle_id": cycle_id,
            "action": action,
            "analysis": analysis,
            "meta_commentary": meta_commentary
        }
        
        if self.client:
            try:
                self.client.table("report").insert(data).execute()
            except Exception as e:
                logger.error(f"[SupabaseReporter] Failed to push report: {e}")
        
        # Always log locally as fallback
        logger.info(f"[REPORT][{cycle_id}] {action} | Analysis: {analysis[:100]}...")

    async def log_event(self, event_type: str, details: dict):
        """Pushes granular execution logs to the logs table."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        if self.client:
            try:
                self.client.table("logs").insert(data).execute()
            except Exception as e:
                logger.error(f"[SupabaseReporter] Failed to push log: {e}")
        
        logger.debug(f"[LOG][{event_type}] {details}")

# Singleton instance
reporter = SupabaseReporter()
