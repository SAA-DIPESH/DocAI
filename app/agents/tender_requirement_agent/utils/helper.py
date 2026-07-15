import json
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List

from app.agents.tender_requirement_agent.graph.agent_state import TenderRequirementState


def read_markdown_file(file_path: Path) -> str:
    """Read markdown file."""

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read().strip()


def read_json_file(file_path: Path) -> Dict[str, Any]:
    """Read json file."""

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_batches(
    chunks: List[Dict[str, Any]],
    batch_size: int,
) -> Iterator[List[Dict[str, Any]]]:
    """Yield batches."""

    for index in range(0, len(chunks), batch_size):
        yield chunks[index:index + batch_size]


def update_latency(
    state: TenderRequirementState,
    node_name: str,
    start_time: float,
) -> Dict[str, float]:
    """Update node latency."""

    latencies = dict(state.get("node_latencies", {}))
    latencies[node_name] = round(
        time.perf_counter() - start_time,
        3,
    )

    return latencies