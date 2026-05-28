import re

path = 'app/db/models.py'
with open(path, 'r') as f:
    content = f.read()

model_code = """

class BackgroundTaskStatus(Base):
    \"\"\"ENG-05: DB-backed persistent background task health monitor\"\"\"
    __tablename__ = "background_task_status"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), default="stopped")  # running, crashed, stopped
    restart_count = Column(Integer, default=0)
    last_started_at = Column(DateTime(timezone=True), nullable=True)
    last_crashed_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(TEXT, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
"""

# Append before the last few lines or at the end
content += model_code

with open(path, 'w') as f:
    f.write(content)
print("BackgroundTaskStatus model added")
