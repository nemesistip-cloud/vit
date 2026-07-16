import re

with open('app/services/rollover_engine.py', 'r') as f:
    content = f.read()

# Rollover already handles Match and Prediction objects.
# It doesn't seem to load pkl files directly; it uses the orchestrator or assumes predictions exist.
# However, if it needs to load a specific model version, we should ensure it can handle tachyon paths.
# Based on current code, RolloverCertifier calls self.simulator and self.xg_resolver.
# Let's check xg_resolver.
