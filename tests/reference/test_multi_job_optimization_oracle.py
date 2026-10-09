"""Stage 2 reference oracle for the four-job objective and schedule."""
import json
import sys
from pathlib import Path

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.optimization import OptimizationJob, prepare_optimization, solve_optimization
from liquidtwin_engine.types import AvailabilityWindow

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import lineup_cpsat as reference


def test_multi_job_optimizer_matches_reference_objective_and_schedule():
    document = json.loads((HERE / "sample-terminal.json").read_text(encoding="utf-8"))
    graph = build_graph(parse_document(document))
    jobs = tuple(
        OptimizationJob(
            id=str(item["id"]),
            direction="IN",
            product_id=str(item["prod"]),
            source_ids=tuple(str(node_id) for node_id in item["src"]),
            destination_ids=tuple(str(node_id) for node_id in item["dst"]),
            volume_m3=item["vol"],
            rate_m3h=item["rate"],
            earliest_start_min=item["eta"],
            due_min=item["etc"],
        )
        for item in reference.JOBS
    )
    prepared = prepare_optimization(graph, jobs)
    availability = tuple(
        AvailabilityWindow(str(element_id), "MAINTENANCE", start_min, end_min)
        for element_id, start_min, end_min in reference.MAINT
    )

    result = solve_optimization(
        graph,
        prepared,
        horizon_minutes=reference.H,
        availability=availability,
        random_seed=1,
    )

    assert result.status == "OPTIMAL"
    assert result.objective == 1327
    assert len(result.scheduled_jobs) == 4
    assert result.kpis["on_time_jobs"] == 4

    uses_by_element = {}
    source_volumes = {}
    destination_volumes = {}
    for scheduled in result.scheduled_jobs:
        job = next(item for item in jobs if item.id == scheduled.job_id)
        source_volumes[scheduled.route.source_id] = (
            source_volumes.get(scheduled.route.source_id, 0) + job.volume_m3
        )
        destination_volumes[scheduled.route.destination_id] = (
            destination_volumes.get(scheduled.route.destination_id, 0) + job.volume_m3
        )
        for element_id in scheduled.route.element_ids:
            uses_by_element.setdefault(element_id, []).append((scheduled, job))

    for element_uses in uses_by_element.values():
        ordered_uses = sorted(element_uses, key=lambda pair: pair[0].start_min)
        for (previous, previous_job), (following, following_job) in zip(
            ordered_uses, ordered_uses[1:]
        ):
            rule = graph.terminal.changeover.get((previous_job.product_id, following_job.product_id))
            gap = rule.gap_min if rule is not None else 0
            assert previous.end_min + gap <= following.start_min

    for tank_id, volume in source_volumes.items():
        tank = graph.terminal.nodes[tank_id]
        if tank.type == "TANK":
            assert volume <= tank.stock_m3
    for tank_id, volume in destination_volumes.items():
        tank = graph.terminal.nodes[tank_id]
        if tank.type == "TANK":
            assert volume <= tank.capacity_m3 - tank.stock_m3