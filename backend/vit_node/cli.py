import click
import asyncio
import sys
from pathlib import Path
from tabulate import tabulate
from vit_node.config import NodeConfig, NODE_CONFIG_DIR
from vit_node.keystore import Keystore
from vit_node.identity import NodeIdentity
from vit_node.storage.gdrive import PersonalDriveStorage
from vit_node.daemon import VITNodeDaemon
from vit_node.earnings.tracker import EarningsTracker
from vit_node.storage.monitor import StorageMonitor
from vit_node.storage.agent import StorageAgent

@click.group()
def cli():
    """VIT Node CLI — Manage your decentralized storage node."""
    pass

@cli.command()
@click.password_option(help="Password to encrypt your keystore.")
def setup(password):
    """First-time node setup."""
    click.echo("Starting VIT Node Setup...")

    # 1. Create keystore
    ks = Keystore()
    if ks.exists():
        if not click.confirm("Keystore already exists. Overwrite?"):
            return

    address = ks.create(password)

    # 2. Show VIT address
    click.echo(f"✅ Keystore created! Your VIT Address: {address}")

    # 3. OAuth Google Drive
    click.echo("Connecting to Google Drive...")
    config = NodeConfig.load()
    # We assume client_secrets.json is provided by user or default
    secrets_path = click.prompt("Path to Google Drive client_secrets.json", default="client_secrets.json")
    drive = PersonalDriveStorage(secrets_path)
    try:
        drive.authenticate()
        config.gdrive_token_path = str(drive.TOKEN_FILE)
        config.save()
        click.echo("✅ Google Drive connected!")
    except Exception as e:
        click.echo(f"❌ Google Drive authentication failed: {e}")
        return

    # 4. Register with VIT Network
    click.echo("Registering node with VIT Network...")
    identity = NodeIdentity(ks, config)
    try:
        asyncio.run(identity.register(password))
        click.echo("✅ Node registered successfully!")
    except Exception as e:
        click.echo(f"❌ Registration failed: {e}")
        return

    click.echo(f"\n✅ Node setup complete! Address: {address}")
    click.echo("Run 'vit-node start' to begin earning VITCoin.")

@cli.command()
@click.password_option(help="Keystore password.")
@click.option("--detach", is_flag=True, help="Run in background.")
def start(password, detach):
    """Start the VIT node daemon."""
    if detach:
        click.echo("Detached mode not implemented in this demo. Starting in foreground...")

    daemon = VITNodeDaemon()
    try:
        asyncio.run(daemon.run(password))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        click.echo(f"❌ Daemon failed: {e}")

@cli.command()
def status():
    """Show node status and earnings."""
    config = NodeConfig.load()
    ks = Keystore()
    if not ks.exists():
        click.echo("❌ Node not setup. Run 'vit-node setup' first.")
        return

    address = ks.get_address()
    drive = PersonalDriveStorage()
    agent = StorageAgent(drive, ks, config)
    monitor = StorageMonitor()
    tracker = EarningsTracker()

    async def get_status_data():
        stats = await monitor.get_stats(agent, drive)
        balance = await tracker.get_balance(address, config.api_url)
        return stats, balance

    try:
        stats, balance = asyncio.run(get_status_data())

        table = [
            ["Node ID", address],
            ["Node Type", config.node_type],
            ["Status", "Online" if stats.get("shards_held", 0) > 0 else "Active/Idle"],
            ["Shards Held", stats["shards_held"]],
            ["Storage Used", f"{stats['storage_used_gb']:.2f} GB"],
            ["Storage Quota", f"{stats['storage_quota_gb']:.2f} GB"],
            ["Balance", f"{balance} VIT"],
            ["Uptime", f"{stats['uptime_pct']}%"]
        ]
        click.echo(tabulate(table, tablefmt="grid"))
    except Exception as e:
        click.echo(f"❌ Failed to fetch status: {e}")

@cli.command()
@click.option("--days", default=30, help="Number of days of history.")
def earnings(days):
    """Show detailed earnings history."""
    config = NodeConfig.load()
    ks = Keystore()
    if not ks.exists():
        click.echo("❌ Node not setup.")
        return

    address = ks.get_address()
    tracker = EarningsTracker()

    try:
        history = asyncio.run(tracker.get_history(address, config.api_url, days))

        if not history:
            click.echo("No earnings history found.")
            return

        table = []
        for tx in history:
            table.append([
                tx.get("timestamp", "N/A"),
                tx.get("type", "N/A"),
                tx.get("amount", "0"),
                tx.get("status", "Confirmed")
            ])

        click.echo(tabulate(table, headers=["Date", "Type", "VIT Earned", "Status"], tablefmt="pretty"))
    except Exception as e:
        click.echo(f"❌ Failed to fetch earnings: {e}")

@cli.command()
def logs():
    """Tail node logs."""
    # Assuming logs are written to a file in NODE_CONFIG_DIR
    log_file = NODE_CONFIG_DIR / "node.log"
    if not log_file.exists():
        click.echo("No logs found.")
        return

    with open(log_file, "r") as f:
        # Simple tail implementation
        lines = f.readlines()
        for line in lines[-50:]:
            click.echo(line.strip())

if __name__ == "__main__":
    cli()
