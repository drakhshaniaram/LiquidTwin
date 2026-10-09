from types import SimpleNamespace
from time import perf_counter

from ortools.sat.python import cp_model

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
import liquidtwin_engine.optimization as optimization
from liquidtwin_engine.optimization import OptimizationJob, prepare_optimization, solve_optimization
from liquidtwin_engine.types import AvailabilityWindow, ExclusionReason as R


def prepare(sample, *jobs):
    graph = build_graph(parse_document(sample))
    return prepare_optimization(graph, jobs)


def test_prepare_job_returns_stage1_candidates_for_review(sample):
    job = OptimizationJob(
        id="job-1",
        direction="IN",
        product_id="1",
        source_ids=("1",),
        destination_ids=("7", "9"),
        volume_m3=4000,
        rate_m3h=1000,
        earliest_start_min=0,
        due_min=400,
    )

    first = prepare(sample, job)[0]
    second = prepare(sample, job)[0]

    assert len(first.routes) == 6
    assert [route.element_ids for route in first.routes] == [route.element_ids for route in second.routes]
    assert first.blockers == ()


def test_prepare_job_keeps_no_route_blockers_visible(sample):
    job = OptimizationJob(
        id="job-no-route",
        direction="IN",
        product_id="2",
        source_ids=("13",),
        destination_ids=("10",),
        volume_m3=500,
        rate_m3h=250,
        earliest_start_min=0,
        due_min=600,
    )

    prepared = prepare(sample, job)[0]

    assert prepared.routes == ()
    assert any(blocker.reason == R.NOT_CERTIFIED for blocker in prepared.blockers)


def test_reference_scenario_is_optimal_with_objective_1327(sample):
    graph = build_graph(parse_document(sample))
    jobs = (
        OptimizationJob("job-1", "IN", "1", ("1",), ("7", "9"), 4000, 1000, 0, 400),
        OptimizationJob("job-2", "IN", "2", ("2",), ("8", "9"), 3000, 800, 30, 600),
        OptimizationJob("job-3", "IN", "1", ("7", "9"), ("10",), 600, 300, 60, 480),
        OptimizationJob("job-4", "IN", "2", ("8", "9"), ("11",), 500, 250, 100, 400),
    )
    prepared = prepare_optimization(graph, jobs)
    maintenance = (AvailabilityWindow("7", "MAINTENANCE", 0, 120),)

    result = solve_optimization(graph, prepared, horizon_minutes=1000, availability=maintenance)
    repeated = solve_optimization(graph, prepared, horizon_minutes=1000, availability=maintenance)

    assert result.status == "OPTIMAL"
    assert result.objective == 1327
    assert len(result.scheduled_jobs) == 4
    assert all(job.late_min == 0 for job in result.scheduled_jobs)
    assert all(job.end_min <= 1000 for job in result.scheduled_jobs)
    assert all(
        "7" not in job.route.element_ids or job.start_min >= 120 or job.end_min <= 0
        for job in result.scheduled_jobs
    )
    assert [
        (job.job_id, job.start_min, job.end_min, job.route.element_ids) for job in result.scheduled_jobs
    ] == [
        (job.job_id, job.start_min, job.end_min, job.route.element_ids) for job in repeated.scheduled_jobs
    ]


def test_solver_returns_no_route_for_a_job_without_candidates(sample):
    graph = build_graph(parse_document(sample))
    job = OptimizationJob("job-no-route", "IN", "2", ("13",), ("10",), 500, 250, 0, 600)
    prepared = prepare_optimization(graph, (job,))

    result = solve_optimization(graph, prepared)

    assert result.status == "NO_ROUTE"
    assert result.scheduled_jobs == ()
    assert result.unscheduled_jobs[0].job_id == job.id
    assert result.unscheduled_jobs[0].blockers


def test_solver_reports_infeasible_horizon_without_partial_schedule(sample):
    graph = build_graph(parse_document(sample))
    job = OptimizationJob("job-too-short", "IN", "1", ("1",), ("7",), 4000, 1000, 0, 30)
    prepared = prepare_optimization(graph, (job,))

    result = solve_optimization(graph, prepared, horizon_minutes=30)

    assert result.status == "INFEASIBLE"
    assert result.scheduled_jobs == ()
    assert result.unscheduled_jobs[0].job_id == job.id
    assert "cannot be scheduled" in result.unscheduled_jobs[0].detail


def test_solver_reports_unknown_when_time_limit_has_no_incumbent(sample, monkeypatch):
    class UnknownSolver:
        def __init__(self):
            self.parameters = SimpleNamespace()

        def Solve(self, _model):
            return cp_model.UNKNOWN

        def StatusName(self, _status):
            return "UNKNOWN"

    monkeypatch.setattr(optimization.cp_model, "CpSolver", UnknownSolver)
    graph = build_graph(parse_document(sample))
    job = OptimizationJob("job-unknown", "IN", "1", ("1",), ("7",), 4000, 1000, 0, 400)
    prepared = prepare_optimization(graph, (job,))

    result = solve_optimization(graph, prepared)

    assert result.status == "UNKNOWN"
    assert result.scheduled_jobs == ()
    assert result.detail.endswith("without finding a feasible incumbent.")


def test_maintenance_ending_at_horizon_start_does_not_block_job(sample):
    graph = build_graph(parse_document(sample))
    job = OptimizationJob("job-after-maintenance", "IN", "1", ("1",), ("7",), 1000, 500, 0, 400)
    prepared = prepare_optimization(graph, (job,))
    availability = (AvailabilityWindow("1", "MAINTENANCE", -120, 0),)

    result = solve_optimization(graph, prepared, availability=availability)

    assert result.status == "OPTIMAL"
    assert result.scheduled_jobs[0].start_min == 0


def test_solver_uses_per_element_sequence_for_multi_dozen_jobs(sample):
    graph = build_graph(parse_document(sample))
    jobs = tuple(
        OptimizationJob(
            f"scale-{index}", "IN", "1", ("1",), ("7",), 1, 1000, 0, 1000
        )
        for index in range(40)
    )
    prepared = prepare_optimization(graph, jobs, max_routes=5)

    started_at = perf_counter()
    result = solve_optimization(graph, prepared, horizon_minutes=1000, time_limit_seconds=5)
    elapsed_seconds = perf_counter() - started_at

    assert result.status in {"OPTIMAL", "FEASIBLE"}
    assert len(result.scheduled_jobs) == 40
    assert elapsed_seconds < 30


def test_solver_labels_incumbent_as_feasible_not_optimal(sample, monkeypatch):
    class IncumbentSolver:
        def __init__(self):
            self.parameters = SimpleNamespace()

        def Solve(self, _model):
            return cp_model.FEASIBLE

        def StatusName(self, _status):
            return "FEASIBLE"

        def BooleanValue(self, variable):
            return variable.Name().startswith("route_") and variable.Name().endswith("_0")

        def Value(self, variable):
            if variable.Name().startswith("end_"):
                return 100
            return 0

        def ObjectiveValue(self):
            return 125

        def BestObjectiveBound(self):
            return 100

    monkeypatch.setattr(optimization.cp_model, "CpSolver", IncumbentSolver)
    graph = build_graph(parse_document(sample))
    job = OptimizationJob("job-feasible", "IN", "1", ("1",), ("7",), 100, 1000, 0, 200)
    prepared = prepare_optimization(graph, (job,))

    result = solve_optimization(graph, prepared)

    assert result.status == "FEASIBLE"
    assert result.objective == 125
    assert result.best_bound == 100
    assert "not proven" in result.detail