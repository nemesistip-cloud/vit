import os

filepath = 'main.py'
with open(filepath, 'r') as f:
    content = f.read()

# Locate the supervised_tasks list and wrap production-incompatible agents in a check
old_tasks = """            supervised_tasks = [
                ("prediction-agent", lambda: importlib.import_module("app.agents.prediction_agent").PredictionAgent().loop()),
                ("performance-monitor", lambda: importlib.import_module("app.agents.performance_monitor").PerformanceMonitorAgent().loop()),
                ("match-scout", lambda: importlib.import_module("app.agents.match_scout_agent").MatchScoutAgent().loop()),
                ("etl-pipeline", etl_pipeline_loop),
                ("odds-refresh", odds_refresh_loop),
                ("cache-purge", lambda: cache_background_purge_loop(300)),
                ("task-reset", task_reset_loop),
            ]"""

new_tasks = """            # In production, heavy agents run in the dedicated worker process (vit-worker).
            # We only run essential maintenance tasks in the API process to save RAM.
            is_prod = get_env("ENVIRONMENT") == "production"

            supervised_tasks = [
                ("etl-pipeline", etl_pipeline_loop),
                ("odds-refresh", odds_refresh_loop),
                ("cache-purge", lambda: cache_background_purge_loop(300)),
                ("task-reset", task_reset_loop),
            ]

            if not is_prod:
                supervised_tasks.extend([
                    ("prediction-agent", lambda: importlib.import_module("app.agents.prediction_agent").PredictionAgent().loop()),
                    ("performance-monitor", lambda: importlib.import_module("app.agents.performance_monitor").PerformanceMonitorAgent().loop()),
                    ("match-scout", lambda: importlib.import_module("app.agents.match_scout_agent").MatchScoutAgent().loop()),
                ])"""

if old_tasks in content:
    content = content.replace(old_tasks, new_tasks)
else:
    print("Exact tasks block not found, check main.py content.")

with open(filepath, 'w') as f:
    f.write(content)
