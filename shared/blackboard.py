import json
import os
import time
from typing import Any


class Blackboard:
    """Registro simples de estados e resultados intermediários do pipeline."""

    def __init__(self, run_id: str, reports_dir: str = "reports") -> None:
        self.run_id = run_id
        self.reports_dir = reports_dir
        self.events: list[dict[str, Any]] = []

    def record(self, url: str, stage: str, status: str, data: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "run_id": self.run_id,
                "url": url,
                "stage": stage,
                "status": status,
                "timestamp": round(time.time(), 3),
                "data": data or {},
            }
        )

    def save(self) -> str:
        os.makedirs(self.reports_dir, exist_ok=True)
        path = os.path.join(self.reports_dir, f"blackboard_{self.run_id[:8]}.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(
                {"run_id": self.run_id, "total_events": len(self.events), "events": self.events},
                file,
                ensure_ascii=False,
                indent=2,
            )
        return path
