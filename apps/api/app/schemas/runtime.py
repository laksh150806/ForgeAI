from datetime import datetime

from pydantic import BaseModel


class RecentRun(BaseModel):
    run_id: str
    created_at: datetime
    repository: str
    task: str
    status: str
    total_duration_ms: int
