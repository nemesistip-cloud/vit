import os

PATH = "app/modules/ai/routes.py"
with open(PATH, "r") as f:
    content = f.read()

# Fix TemperatureScaler.load() calls to await
content = content.replace("TemperatureScaler.load().temperature", "(await TemperatureScaler.load()).temperature")

with open(PATH, "w") as f:
    f.write(content)
