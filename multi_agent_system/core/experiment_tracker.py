"""
Experiment Tracker - Inspired by karpathy/autoresearch

Tracks task outcomes in a structured log (TSV + JSON) for long-running
autonomous loops. Enables the system to learn from past experiments:
what worked, what failed, and what to try next.
"""
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """Tracks experiment results in TSV format for autonomous loop analysis.

    Inspired by autoresearch's results.tsv: each task completion is an
    "experiment" with a keep/discard/crash outcome.
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._tsv_path = self._data_dir / "experiment_results.tsv"
        self._json_log_path = self._data_dir / "experiment_log.jsonl"

        self._ensure_tsv_header()
        self._experiment_count = 0

    def _ensure_tsv_header(self):
        """Create TSV file with header if it doesn't exist"""
        if not self._tsv_path.exists():
            with open(self._tsv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter="\t")
                writer.writerow([
                    "timestamp",
                    "task_id",
                    "description",
                    "outcome",       # keep | discard | crash
                    "quality_score",
                    "duration_sec",
                    "subtask_count",
                    "provider",
                    "notes",
                ])

    def record(
        self,
        task_id: str,
        description: str,
        outcome: str,
        quality_score: Optional[int] = None,
        duration_sec: Optional[float] = None,
        subtask_count: int = 0,
        provider: str = "unknown",
        notes: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Record an experiment result.

        Args:
            task_id: Task identifier
            description: What the task aimed to do
            outcome: "keep" (success), "discard" (failed but no crash),
                     "crash" (unexpected error)
            quality_score: 1-10 quality rating from analysis
            duration_sec: How long the task took
            subtask_count: Number of subtasks generated
            provider: LLM provider used
            notes: Free-form notes
            extra: Additional JSON-serializable data
        """
        timestamp = datetime.now().isoformat()
        self._experiment_count += 1

        # Write TSV row
        try:
            with open(self._tsv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter="\t")
                writer.writerow([
                    timestamp,
                    task_id,
                    description[:200],
                    outcome,
                    quality_score or "",
                    f"{duration_sec:.1f}" if duration_sec else "",
                    subtask_count,
                    provider,
                    notes[:300],
                ])
        except Exception as e:
            logger.error(f"Failed to write TSV experiment log: {e}")

        # Write JSONL (richer detail)
        try:
            record = {
                "timestamp": timestamp,
                "task_id": task_id,
                "description": description,
                "outcome": outcome,
                "quality_score": quality_score,
                "duration_sec": duration_sec,
                "subtask_count": subtask_count,
                "provider": provider,
                "notes": notes,
                "experiment_number": self._experiment_count,
            }
            if extra:
                record["extra"] = extra

            with open(self._json_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write JSONL experiment log: {e}")

        logger.info(
            f"Experiment #{self._experiment_count}: {outcome} "
            f"[{task_id}] quality={quality_score}"
        )

    def get_recent(self, n: int = 20) -> List[Dict[str, Any]]:
        """Get the N most recent experiment results from JSONL log."""
        results = []
        try:
            if self._json_log_path.exists():
                with open(self._json_log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in lines[-n:]:
                    try:
                        results.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read experiment log: {e}")
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics across all experiments."""
        results = self.get_recent(n=10000)
        if not results:
            return {"total": 0}

        outcomes = {}
        quality_scores = []
        durations = []

        for r in results:
            outcome = r.get("outcome", "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            if r.get("quality_score"):
                try:
                    quality_scores.append(int(r["quality_score"]))
                except (ValueError, TypeError):
                    pass
            if r.get("duration_sec"):
                try:
                    durations.append(float(r["duration_sec"]))
                except (ValueError, TypeError):
                    pass

        return {
            "total": len(results),
            "outcomes": outcomes,
            "avg_quality": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "avg_duration_sec": sum(durations) / len(durations) if durations else None,
            "success_rate": outcomes.get("keep", 0) / len(results) if results else 0,
        }
