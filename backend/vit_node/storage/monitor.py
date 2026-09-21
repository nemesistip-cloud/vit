import asyncio
import httpx
import time
from datetime import datetime
from vit_node.storage.agent import StorageAgent
from vit_node.storage.gdrive import PersonalDriveStorage

class StorageMonitor:
    def __init__(self):
        self.challenges_responded_today = 0
        self.challenges_correct_today = 0
        self.start_time = time.time()

    async def get_stats(self, agent: StorageAgent,
                         drive: PersonalDriveStorage) -> dict:
        usage = await drive.get_usage()
        shards = await agent.get_assigned_shards()

        # In a real app, these would be fetched from the server or local DB
        node_id = agent.keystore.get_address()
        server_stats = {}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{agent.config.api_url}/api/chain/peers/{node_id}/stats")
                if response.status_code == 200:
                    server_stats = response.json()
            except Exception:
                pass

        uptime_seconds = time.time() - self.start_time

        return {
            "shards_held": len(shards),
            "storage_used_gb": usage.get("vit_node_folder_bytes", 0) / (1024**3),
            "storage_quota_gb": usage.get("quota_bytes", 0) / (1024**3),
            "challenges_responded_today": self.challenges_responded_today,
            "challenges_correct_today": server_stats.get("challenges_correct_today", self.challenges_correct_today),
            "uptime_pct": server_stats.get("uptime_pct", 100.0), # Simplified
            "earnings_today_vit": server_stats.get("earnings_today_vit", 0.0),
            "earnings_total_vit": server_stats.get("earnings_total_vit", 0.0),
        }

    async def monitor_loop(self, agent: StorageAgent):
        """
        Every 60 seconds:
          Check all assigned shards are still accessible
          Report any missing shards to server
          POST /api/tachyon/node/health_report
        """
        while True:
            try:
                shards = await agent.get_assigned_shards()
                healthy_shards = []
                missing_shards = []

                for shard in shards:
                    shard_id = shard.get("shard_id")
                    file_id = shard.get("file_id")

                    # We don't want to download every shard every minute (too much egress/bandwidth)
                    # For a basic health check, we just check if the file exists in Drive
                    try:
                        # This checks if file is accessible
                        await asyncio.to_thread(agent.drive.service.files().get(fileId=file_id, fields="id").execute)
                        healthy_shards.append(shard_id)
                    except Exception:
                        missing_shards.append(shard_id)

                node_id = agent.keystore.get_address()
                payload = {
                    "node_id": node_id,
                    "shards_healthy": healthy_shards,
                    "shards_missing": missing_shards,
                    "timestamp": datetime.utcnow().isoformat()
                }

                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{agent.config.api_url}/api/tachyon/node/health_report",
                        json=payload,
                        timeout=30.0
                    )
            except Exception:
                # Log error or wait for next loop
                pass

            await asyncio.sleep(60)
