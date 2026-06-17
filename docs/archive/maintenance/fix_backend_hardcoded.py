import os
import re

def replace_in_file(filepath, pattern, replacement):
    if not os.path.exists(filepath): return
    with open(filepath, "r") as f:
        content = f.read()
    new_content = content.replace(pattern, replacement)
    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Updated {filepath}")

files_to_fix = [
    ("app/services/calibration.py", "the 13-model ensemble", "the VIT ensemble"),
    ("app/services/deterministic_insights.py", "the 13-model ensemble", "the VIT ensemble"),
    ("app/services/accuracy_enhancer.py", "the 13-model ensemble", "the VIT ensemble"),
    ("app/app/__init__.py", "13-Model Ensemble", "ML Ensemble"),
    ("app/core/seeding.py", "VIT's 13-model ensemble", "the VIT ensemble"),
    ("app/__init__.py", "13-Model Ensemble", "ML Ensemble"),
    ("app/training/prompt_generator.py", "the VIT 13-model ensemble", "the VIT ensemble"),
]

for filepath, pattern, replacement in files_to_fix:
    replace_in_file(filepath, pattern, replacement)
