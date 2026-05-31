import json

def validate_features(features: dict) -> bool:
    """
    Validates a dictionary of features against predefined criteria.

    Args:
        features (dict): A dictionary of engineered features.

    Returns:
        bool: True if all features are valid, False otherwise.
    """
    if not features:
        print("Validation failed: Features dictionary is empty.")
        return False

    validation_rules = {
        "home_form": {"type": "int", "min": 0, "max": 100},
        "away_form": {"type": "int", "min": 0, "max": 100},
        "weather_temp_c": {"type": "float", "min": -50.0, "max": 50.0, "nullable": True},
        "injury_count_home": {"type": "int", "min": 0, "max": 20},
        "injury_count_away": {"type": "int", "min": 0, "max": 20},
        "sentiment_score_home": {"type": "float", "min": -1.0, "max": 1.0, "nullable": True},
        "avg_goals_per_player_home": {"type": "float", "min": 0.0, "max": 5.0, "nullable": True},
        "home_odds_change_pct": {"type": "float", "min": -1.0, "max": 1.0, "nullable": True}
    }

    is_valid = True
    for feature_name, rules in validation_rules.items():
        value = features.get(feature_name)

        if value is None:
            if not rules.get("nullable", False):
                print(f"Validation failed for '{feature_name}': Cannot be null.")
                is_valid = False
            continue

        expected_type = rules.get("type")
        if expected_type == "int" and not isinstance(value, int):
            print(f"Validation failed for '{feature_name}': Expected type {expected_type}, got {type(value).__name__}.")
            is_valid = False
            continue
        if expected_type == "float" and not isinstance(value, (int, float)):
            print(f"Validation failed for '{feature_name}': Expected type {expected_type}, got {type(value).__name__}.")
            is_valid = False
            continue

        min_val = rules.get("min")
        max_val = rules.get("max")
        if min_val is not None and value < min_val:
            print(f"Validation failed for '{feature_name}': Value {value} is below min {min_val}.")
            is_valid = False
        if max_val is not None and value > max_val:
            print(f"Validation failed for '{feature_name}': Value {value} is above max {max_val}.")
            is_valid = False

    return is_valid
