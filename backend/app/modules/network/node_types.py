"""Node Type Registry — defines hardware requirements and reward multipliers."""

NODE_TYPES = {
    "storage": {
        "display": "Storage Node",
        "description": "Contributes Google Drive storage",
        "min_storage_gb": 5,
        "min_stake_vit": 0,
        "reward_multiplier": 1.0,
    },
    "validator": {
        "display": "Validator Node",
        "description": "Campus Rep — validates + stores",
        "min_storage_gb": 10,
        "min_stake_vit": 100,
        "reward_multiplier": 2.0,
    },
    "campus": {
        "display": "Campus Node",
        "description": "University server infrastructure",
        "min_storage_gb": 50,
        "min_stake_vit": 500,
        "reward_multiplier": 3.0,
    },
    "android": {
        "display": "Mobile Node",
        "description": "Android device — lightweight",
        "min_storage_gb": 1,
        "min_stake_vit": 0,
        "reward_multiplier": 0.5,
    },
    "gpu": {
        "display": "GPU Node",
        "description": "Compute node for AI inference",
        "min_storage_gb": 20,
        "min_stake_vit": 1000,
        "reward_multiplier": 5.0,
    },
}
