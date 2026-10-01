from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

script_path = Path(__file__).parents[1] / "scripts/retrain_cron.py"
script_spec = spec_from_file_location("vit_retrain_cron", script_path)
retrain_cron = module_from_spec(script_spec)
script_spec.loader.exec_module(retrain_cron)


def test_training_cron_loads_the_repository_manifest():
    assert retrain_cron.MANIFEST.is_file()
    entries = retrain_cron.load_manifest()
    assert entries
    assert all((retrain_cron.ROOT / entry["path"]).is_file() for entry in entries)


def test_synthetic_manifest_entries_are_not_training_eligible():
    entries = retrain_cron.load_manifest()
    ineligible_entries = [
        entry
        for entry in entries
        if entry.get("training_eligible") is False
    ]
    ineligible_datasets = {(entry["sport"], entry["name"]) for entry in ineligible_entries}

    assert ineligible_datasets == {
        ("american_football", "NFL matches"),
        ("basketball", "EuroLeague matches"),
        ("rugby", "Rugby matches"),
    }
    assert all(not retrain_cron.is_training_eligible(entry) for entry in ineligible_entries)
    assert any(entry["name"] == "NBA matches" and retrain_cron.is_training_eligible(entry) for entry in entries)


def test_same_sport_datasets_write_distinct_model_artifacts():
    entries = retrain_cron.load_manifest()
    tennis_entries = [entry for entry in entries if entry["sport"] == "tennis"]
    artifacts = {retrain_cron.model_artifact_path(entry) for entry in tennis_entries}

    assert len(tennis_entries) == 2
    assert artifacts == {
        retrain_cron.ROOT / "models" / "atp_matches_baseline.pkl",
        retrain_cron.ROOT / "models" / "wta_matches_baseline.pkl",
    }