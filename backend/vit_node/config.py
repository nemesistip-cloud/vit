import json
from pathlib import Path
from dataclasses import dataclass, asdict
from app.config import get_env
from app.core.errors import AppError

NODE_CONFIG_DIR = Path.home() / ".vit_node"
KEYSTORE_FILE = NODE_CONFIG_DIR / "keystore.json"
CONFIG_FILE = NODE_CONFIG_DIR / "config.json"

VIT_API_URL = get_env("VIT_API_URL", "https://vit.network")
VIT_P2P_URL = get_env("VIT_P2P_URL", "wss://vit.network/api/chain/peer")

@dataclass
class NodeConfig:
    api_url: str = VIT_API_URL
    p2p_url: str = VIT_P2P_URL
    node_type: str = "storage"  # "storage" | "validator"
    gdrive_token_path: str | None = None
    earn_mode: bool = True
    max_storage_gb: float = 10.0
    data_dir: Path = NODE_CONFIG_DIR / "data"
    registration_result: dict | None = None

    @classmethod
    def load(cls) -> "NodeConfig":
        if not CONFIG_FILE.exists():
            return cls()

        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)

            if "data_dir" in data:
                data["data_dir"] = Path(data["data_dir"])

            return cls(**data)
        except Exception as e:
            # We return defaults but could raise AppError if it's critical
            # Given it's a node config, falling back to default is often safer for startup
            # but we should probably warn or raise if it's a parse error in a real file.
            if CONFIG_FILE.exists():
                 raise AppError(f"Failed to load config: {str(e)}", code="config_load_error")
            return cls()

    def save(self):
        try:
            NODE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = asdict(self)
            data["data_dir"] = str(data["data_dir"])

            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise AppError(f"Failed to save config: {str(e)}", code="config_save_error")
