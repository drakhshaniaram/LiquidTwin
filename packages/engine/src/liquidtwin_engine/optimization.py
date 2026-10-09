"""Request-scoped multi-job route preparation and CP-SAT scheduling."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from ortools.sat.python import cp_model

from .graph import TerminalGraph
from .routing import route_job
from .types import AvailabilityWindow, Exclusion, Route, RouteRequest


@dataclass(frozen=True)
class OptimizationJob:
    id: str
    direction: str
    product_id: str
    source_ids: tuple[str, ...]
    destination_ids: tuple[str, ...]
    volume_m3: float
    rate_m3h: float
    earliest_start_min: int
    due_min: int
    pump_suction_inputs: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class PreparedJob:
    job: OptimizationJob
    routes: tuple[Route, ...]
    blockers: tuple[Exclusion, ...] = ()


@dataclass(frozen=True)
class ObjectiveWeights:
    waiting: int = 1
    lateness: int = 20
    flush_volume: int = 1
    valves: int = 2
    shared_headers: int = 3


@dataclass(frozen=True)
class ScheduledJob:
    job_id: str
    route: Route
    start_min: int
    end_min: int
    late_min: int


@dataclass(frozen=True)
class UnscheduledJob:
    job_id: str
    detail: str
    blockers: tuple[Exclusion, ...] = ()
    conflict_elements: tuple[str, ...] = ()


@dataclass(frozen=True)
class ElementUseInterval:
    element_id: str
    job_id: str
    product_id: str
    start_min: int
    end_min: int


@dataclass(frozen=True)
class OptimizationResult:
    status: str
    objective: int | None
    best_bound: int | None
    scheduled_jobs: tuple[ScheduledJob, ...]
    unscheduled_jobs: tuple[UnscheduledJob, ...]
    kpis: dict[str, int]
    element_timeline: tuple[ElementUseInterval, ...]
    detail: str


def prepare_optimization(
    graph: TerminalGraph,
    jobs: tuple[OptimizationJob, ...],
    max_routes: int = 20,
) -> tuple[PreparedJob, ...]:
    """Generate deterministic Stage 1 candidates; scheduling constraints are applied later."""
    prepared: list[PreparedJob] = []
    for job in jobs:
        request = RouteRequest(
            direction=job.direction,
            product_id=job.product_id,
            volume_m3=job.volume_m3,
            rate_m3h=job.rate_m3h,
            window_from_min=job.earliest_start_min,
            source_ids=job.source_ids,
            destination_ids=job.destination_ids,
            max_routes=max_routes,
            pump_suction_inputs=job.pump_suction_inputs,
        )
        result = route_job(graph, request)
        blockers = tuple(result.no_route.blockers) if result.no_route is not None else ()
        if not result.routes and not blockers:
            blockers = tuple(result.exclusions)
        prepared.append(PreparedJob(job, tuple(result.routes), blockers))
    return tuple(prepared)


def solve_optimization(
    graph: TerminalGraph,
    prepared_jobs: tuple[PreparedJob, ...],
    horizon_minutes: int = 1000,
    availability: Sequence[AvailabilityWindow] = (),
    weights: ObjectiveWeights = ObjectiveWeights(),
    time_limit_seconds: float = 30,
    random_seed: int = 1,
) -> OptimizationResult:
    """Select one Stage 1 route per job and schedule shared resources with CP-SAT."""
    if horizon_minutes < 1 or not 0 < time_limit_seconds <= 30:
        raise ValueError("horizon_minutes and time_limit_seconds are outside supported limits")
    if any(value < 0 for value in asdict(weights).values()):
        raise ValueError("objective weights must be nonnegative")
    if len({item.job.id for item in prepared_jobs}) != len(prepared_jobs):
        raise ValueError("job IDs must be unique within a scenario")

    jobs_without_routes = tuple(item for item in prepared_jobs if not item.routes)
    if jobs_without_routes:
        return OptimizationResult(
            status="NO_ROUTE",
            objective=None,
            best_bound=None,
            scheduled_jobs=(),
            unscheduled_jobs=tuple(
                UnscheduledJob(
                    item.job.id,
                    "No Stage 1 route candidate is feasible for this job",
                    item.blockers,
                )
                for item in jobs_without_routes
            ),
            kpis={"on_time_jobs": 0, "total_lateness_min": 0, "waiting_min": 0, "flush_volume_m3": 0, "makespan_min": 0},
            element_timeline=(),
            detail="One or more jobs have no feasible Stage 1 route candidate.",
        )

    model: Any = cp_model.CpModel()
    starts: list[cp_model.IntVar] = []
    ends: list[cp_model.IntVar] = []
    lateness: list[cp_model.IntVar] = []
    assumptions: list[cp_model.IntVar] = []
    assumption_to_job: dict[int, str] = {}
    route_literals: dict[tuple[int, int], cp_model.IntVar] = {}
    objective_terms = []

    for job_index, prepared in enumerate(prepared_jobs):
        job = prepared.job
        if job.earliest_start_min > horizon_minutes or job.due_min > horizon_minutes:
            raise ValueError(f"Job {job.id} ETA/due time is outside the planning horizon")
        assumption = model.NewBoolVar(f"required_{job.id}")
        model.AddAssumption(assumption)
        assumptions.append(assumption)
        assumption_to_job[assumption.Index()] = job.id

        start = model.NewIntVar(job.earliest_start_min, horizon_minutes, f"start_{job.id}")
        end = model.NewIntVar(0, horizon_minutes, f"end_{job.id}")
        late = model.NewIntVar(0, horizon_minutes, f"late_{job.id}")
        starts.append(start)
        ends.append(end)
        lateness.append(late)
        model.Add(late >= end - job.due_min).OnlyEnforceIf(assumption)
        objective_terms.append(weights.waiting * (end - job.earliest_start_min))
        objective_terms.append(weights.lateness * late)

        literals = []
        for route_index, route in enumerate(prepared.routes):
            literal = model.NewBoolVar(f"route_{job.id}_{route_index}")
            route_literals[(job_index, route_index)] = literal
            literals.append(literal)
            model.AddImplication(literal, assumption)
            duration = int(round(route.metrics.total_min))
            model.Add(end == start + duration).OnlyEnforceIf(literal)
            route_cost = (
                weights.flush_volume * int(round(route.metrics.flush_volume_m3))
                + weights.valves * route.metrics.valves
                + weights.shared_headers * route.metrics.common_headers
            )
            objective_terms.append(route_cost * literal)
        model.AddExactlyOne(literals).OnlyEnforceIf(assumption)

    resource_intervals: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
    resource_usage_literals: dict[str, dict[int, cp_model.IntVar]] = defaultdict(dict)
    for (job_index, route_index), literal in route_literals.items():
        prepared = prepared_jobs[job_index]
        route = prepared.routes[route_index]
        duration = int(round(route.metrics.total_min))
        for element_id in set(route.element_ids):
            interval = model.NewOptionalIntervalVar(
                starts[job_index],
                duration,
                starts[job_index] + duration,
                literal,
                f"use_{element_id}_{prepared.job.id}_{route_index}",
            )
            resource_intervals[element_id].append(interval)
            terms = resource_usage_literals[element_id]
            terms[job_index] = model.NewBoolVar(f"uses_{element_id}_{prepared.job.id}")

    for element_id, usage in resource_usage_literals.items():
        for job_index, use_literal in usage.items():
            route_uses = [
                route_literals[(job_index, route_index)]
                for route_index, route in enumerate(prepared_jobs[job_index].routes)
                if element_id in route.element_ids
            ]
            model.Add(use_literal == sum(route_uses))

        maintenance_intervals = []
        for window_index, window in enumerate(availability):
            if window.kind != "ELEMENT" or window.element_id != element_id or window.status == "AVAILABLE":
                continue
            block_start = max(0, math.ceil(window.start_min))
            block_end_minute = window.end_min if window.end_min is not None else horizon_minutes
            block_end = min(horizon_minutes, math.ceil(block_end_minute))
            if block_end > block_start:
                maintenance_intervals.append(
                    model.NewIntervalVar(
                        block_start,
                        block_end - block_start,
                        block_end,
                        f"maintenance_{element_id}_{window_index}",
                    )
                )
        if maintenance_intervals:
            resource_intervals[element_id].extend(maintenance_intervals)
        model.AddNoOverlap(resource_intervals[element_id])

        active_jobs = sorted(usage)
        if len(active_jobs) < 2:
            continue
        requires_sequence = any(
            (changeover := graph.terminal.changeover.get(
                (
                    prepared_jobs[previous_index].job.product_id,
                    prepared_jobs[next_index].job.product_id,
                )
            ))
            is not None
            and (changeover.manual_clean_required or changeover.gap_min > 0)
            for previous_index in active_jobs
            for next_index in active_jobs
            if previous_index != next_index
        )
        if not requires_sequence:
            continue
        circuit_arcs = [(0, 0, model.NewBoolVar(f"empty_{element_id}"))]
        for job_index in active_jobs:
            circuit_node = job_index + 1
            use_literal = usage[job_index]
            circuit_arcs.append((circuit_node, circuit_node, use_literal.Not()))
            first = model.NewBoolVar(f"first_{element_id}_{job_index}")
            last = model.NewBoolVar(f"last_{element_id}_{job_index}")
            model.AddImplication(first, use_literal)
            model.AddImplication(last, use_literal)
            circuit_arcs.extend(((0, circuit_node, first), (circuit_node, 0, last)))
        for previous_index in active_jobs:
            for next_index in active_jobs:
                if previous_index == next_index:
                    continue
                successor = model.NewBoolVar(f"next_{element_id}_{previous_index}_{next_index}")
                model.AddImplication(successor, usage[previous_index])
                model.AddImplication(successor, usage[next_index])
                circuit_arcs.append((previous_index + 1, next_index + 1, successor))
                previous_job = prepared_jobs[previous_index].job
                next_job = prepared_jobs[next_index].job
                changeover = graph.terminal.changeover.get(
                    (previous_job.product_id, next_job.product_id)
                )
                if changeover is not None and changeover.manual_clean_required:
                    model.Add(successor == 0)
                else:
                    gap = math.ceil(changeover.gap_min) if changeover is not None else 0
                    model.Add(starts[next_index] >= ends[previous_index] + gap).OnlyEnforceIf(successor)
        model.AddCircuit(circuit_arcs)

    for job_index, prepared in enumerate(prepared_jobs):
        for route_index, route in enumerate(prepared.routes):
            literal = route_literals[(job_index, route_index)]
            duration = int(round(route.metrics.total_min))
            for window_index, window in enumerate(availability):
                if window.kind != "NODE" or window.status == "AVAILABLE":
                    continue
                if window.element_id not in {route.source_id, route.destination_id}:
                    continue
                block_start = max(0, math.ceil(window.start_min))
                block_end_minute = window.end_min if window.end_min is not None else horizon_minutes
                block_end = min(horizon_minutes, math.ceil(block_end_minute))
                if block_end <= block_start:
                    continue
                before = model.NewBoolVar(f"node_before_{job_index}_{route_index}_{window_index}")
                model.Add(starts[job_index] + duration <= block_start).OnlyEnforceIf([literal, before])
                model.Add(starts[job_index] >= block_end).OnlyEnforceIf([literal, before.Not()])

    inventory_scale = 1000
    for node in graph.terminal.nodes.values():
        if node.type != "TANK":
            continue
        outbound = []
        inbound = []
        for (job_index, route_index), literal in route_literals.items():
            route = prepared_jobs[job_index].routes[route_index]
            volume = int(round(prepared_jobs[job_index].job.volume_m3 * inventory_scale))
            if route.source_id == node.id:
                outbound.append(volume * literal)
            if route.destination_id == node.id:
                inbound.append(volume * literal)
        if outbound:
            model.Add(sum(outbound) <= int(round(node.stock_m3 * inventory_scale)))
        if inbound:
            free_space = max(0, node.capacity_m3 - node.stock_m3)
            model.Add(sum(inbound) <= int(round(free_space * inventory_scale)))

    model.Minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = random_seed
    status_code = solver.Solve(model)
    status = solver.StatusName(status_code)

    if status_code == cp_model.INFEASIBLE:
        core = solver.SufficientAssumptionsForInfeasibility()
        conflict_jobs = set()
        for literal_index in core:
            job_id = assumption_to_job.get(
                literal_index if literal_index >= 0 else -literal_index - 1
            )
            if job_id is not None:
                conflict_jobs.add(job_id)
        if not conflict_jobs:
            conflict_jobs = {item.job.id for item in prepared_jobs}
        core_items = [item for item in prepared_jobs if item.job.id in conflict_jobs]
        possible_resources = [
            {element_id for route in item.routes for element_id in route.element_ids}
            for item in core_items
        ]
        conflict_elements = sorted(set.intersection(*possible_resources)) if len(possible_resources) > 1 else []
        return OptimizationResult(
            status="INFEASIBLE",
            objective=None,
            best_bound=None,
            scheduled_jobs=(),
            unscheduled_jobs=tuple(
                UnscheduledJob(
                    job_id,
                    "Required jobs cannot be scheduled together within the horizon and resource constraints",
                    conflict_elements=tuple(conflict_elements),
                )
                for job_id in sorted(conflict_jobs)
            ),
            kpis={"on_time_jobs": 0, "total_lateness_min": 0, "waiting_min": 0, "flush_volume_m3": 0, "makespan_min": 0},
            element_timeline=(),
            detail="The required jobs cannot be scheduled together within the horizon and resource constraints.",
        )
    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return OptimizationResult(
            status=status,
            objective=None,
            best_bound=None,
            scheduled_jobs=(),
            unscheduled_jobs=(),
            kpis={"on_time_jobs": 0, "total_lateness_min": 0, "waiting_min": 0, "flush_volume_m3": 0, "makespan_min": 0},
            element_timeline=(),
            detail="The solver reached its limit without finding a feasible incumbent.",
        )

    scheduled: list[ScheduledJob] = []
    timeline: list[ElementUseInterval] = []
    total_waiting = 0
    total_lateness = 0
    total_flush = 0
    for job_index, prepared in enumerate(prepared_jobs):
        route_index = next(
            index
            for index in range(len(prepared.routes))
            if solver.BooleanValue(route_literals[(job_index, index)])
        )
        route = prepared.routes[route_index]
        start_min = solver.Value(starts[job_index])
        end_min = solver.Value(ends[job_index])
        late_min = max(0, end_min - prepared.job.due_min)
        scheduled.append(ScheduledJob(prepared.job.id, route, start_min, end_min, late_min))
        total_waiting += start_min - prepared.job.earliest_start_min
        total_lateness += late_min
        total_flush += int(round(route.metrics.flush_volume_m3))
        timeline.extend(
            ElementUseInterval(element_id, prepared.job.id, prepared.job.product_id, start_min, end_min)
            for element_id in route.element_ids
        )
    scheduled.sort(key=lambda item: (item.start_min, item.job_id))
    timeline.sort(key=lambda item: (item.element_id, item.start_min, item.job_id))
    return OptimizationResult(
        status=status,
        objective=int(round(solver.ObjectiveValue())),
        best_bound=int(round(solver.BestObjectiveBound())),
        scheduled_jobs=tuple(scheduled),
        unscheduled_jobs=(),
        kpis={
            "on_time_jobs": sum(job.late_min == 0 for job in scheduled),
            "total_lateness_min": total_lateness,
            "waiting_min": total_waiting,
            "flush_volume_m3": total_flush,
            "makespan_min": max((job.end_min for job in scheduled), default=0),
        },
        element_timeline=tuple(timeline),
        detail=(
            "Optimality proven."
            if status_code == cp_model.OPTIMAL
            else "Feasible incumbent found; optimality is not proven."
        ),
    )