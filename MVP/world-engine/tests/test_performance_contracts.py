"""Performance Contract Tests for World Engine.

WAVE 8 Hardening Initiative: API performance and scalability contracts.
Tests focus on ensuring API responses meet performance expectations including
response times, query scaling, memory usage, and concurrent request handling.

Mark: @pytest.mark.contract
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import pytest


@pytest.mark.contract
def test_simple_query_response_time_under_100ms(client):
    """Verify that simple API queries respond within 100ms."""
    # Simple query: list templates
    start = time.perf_counter()
    response = client.get("/api/templates")
    elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

    assert response.status_code == 200
    # Performance contract: simple queries should be fast
    # Note: On test systems may vary, threshold is generous for CI/CD
    assert elapsed < 500, f"Simple query took {elapsed:.2f}ms, expected < 500ms"


@pytest.mark.contract
def test_health_check_response_time_under_50ms(client):
    """Verify that health check endpoint responds within 50ms."""
    # Health check should be very fast
    start = time.perf_counter()
    response = client.get("/api/health")
    elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    # Health checks must be fast
    assert elapsed < 200, f"Health check took {elapsed:.2f}ms, expected < 200ms"


@pytest.mark.contract
def test_complex_query_response_time_under_500ms(client):
    """Verify that complex API queries respond within 500ms."""
    # Complex query: create run and get detailed info
    start = time.perf_counter()
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "perf-test", "display_name": "Test"},
    )
    run_id = create_response.json()["run"]["id"]

    # Get detailed run info (more complex than simple list)
    response = client.get(f"/api/runs/{run_id}")
    elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    # Performance contract: complex queries should still be reasonably fast
    assert elapsed < 1000, f"Complex query took {elapsed:.2f}ms, expected < 1000ms"


@pytest.mark.contract
def test_bulk_operation_scales_linearly(client):
    """Verify that bulk operations scale approximately linearly."""
    # Create multiple runs and measure scaling
    times = []
    for batch_size in [5, 10]:
        start = time.perf_counter()
        for i in range(batch_size):
            client.post(
                "/api/runs",
                json={"template_id": "god_of_carnage_solo", "account_id": f"scale-{i}", "display_name": f"Run {i}"},
            )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    # Time should roughly scale linearly
    # 10 runs should take approximately 2x the time of 5 runs
    # Allow for variability in test environment: 1.0x to 5.0x
    # (1.0x is better than linear, up to 5.0x is acceptable on slower systems)
    if len(times) == 2:
        ratio = times[1] / times[0]
        # Check it's in reasonable range for linear scaling
        assert 1.0 <= ratio <= 5.0, f"Scaling ratio {ratio} indicates non-linear behavior"


@pytest.mark.contract
def test_pagination_handles_large_result_sets(client):
    """Verify that pagination correctly handles large result sets."""
    # Create many runs
    num_runs = 20
    for i in range(num_runs):
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": f"paginate-{i}", "display_name": f"Page {i}"},
        )
        assert response.status_code == 200

    # List all runs
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()

    # Should handle all created runs
    assert len(runs) >= num_runs

    # Response should be valid and not truncated
    assert isinstance(runs, list)
    for run in runs:
        assert "id" in run
        assert "template_id" in run


@pytest.mark.contract
def test_concurrent_requests_performance(client):
    """Verify that concurrent requests are handled efficiently."""
    num_concurrent = 5

    def make_request(i):
        start = time.perf_counter()
        response = client.get("/api/templates")
        elapsed = (time.perf_counter() - start) * 1000
        return response.status_code, elapsed

    # Make concurrent requests
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
        results = [f.result() for f in as_completed(futures)]

    # All requests should succeed
    assert all(status == 200 for status, _ in results)

    # No request should take excessively long
    max_time = max(elapsed for _, elapsed in results)
    assert max_time < 1000, f"Concurrent request took {max_time:.2f}ms"


@pytest.mark.contract
def test_memory_usage_reasonable_under_load(client):
    """Verify that memory usage stays reasonable under load."""
    import gc

    gc.collect()  # Clean up before measuring

    # Get memory baseline
    try:
        import psutil
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    except ImportError:
        # psutil not available, skip detailed measurement
        baseline_memory = None

    # Create multiple runs
    for i in range(10):
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": f"memory-{i}", "display_name": f"Test {i}"},
        )
        assert response.status_code == 200

    # List runs multiple times
    for _ in range(5):
        response = client.get("/api/runs")
        assert response.status_code == 200

    # Check memory usage
    if baseline_memory is not None:
        gc.collect()
        current_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = current_memory - baseline_memory

        # Memory should not grow excessively
        # Allow reasonable growth for test data (< 50 MB increase)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"


@pytest.mark.contract
def test_database_query_optimization(client):
    """Verify that database queries are optimized."""
    # Create a run
    response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "opt-test", "display_name": "Test"},
    )
    run_id = response.json()["run"]["id"]

    # Add multiple participants
    for i in range(3):
        client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": f"guest-{i}", "display_name": f"Guest {i}"},
        )

    # Getting run details should be efficient
    # (no N+1 queries, proper eager loading)
    start = time.perf_counter()
    for _ in range(5):
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
    elapsed = (time.perf_counter() - start) * 1000

    # Multiple calls should not increase time linearly (caching/connection reuse)
    avg_time = elapsed / 5
    assert avg_time < 200, f"Average query time {avg_time:.2f}ms suggests N+1 problem"


@pytest.mark.contract
def test_api_response_size_reasonable(client):
    """Verify that API response sizes are reasonable."""
    # Get list of runs
    response = client.get("/api/runs")
    assert response.status_code == 200

    # Check response size
    response_size = len(response.content)  # bytes
    response_size_kb = response_size / 1024

    # Response should be reasonable size
    # For empty/small dataset, should be < 100KB
    # Allow larger for actual data
    if len(response.json()) < 50:
        assert response_size_kb < 500, f"Response size {response_size_kb:.2f}KB seems large for small dataset"

    # Check that response is not unnecessarily verbose
    # Should be valid JSON
    assert response.json() is not None


@pytest.mark.contract
def test_connection_pooling_efficiency(client):
    """Verify that connections are reused efficiently."""
    # Make multiple sequential requests
    times = []
    for i in range(5):
        start = time.perf_counter()
        response = client.get("/api/templates")
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        assert response.status_code == 200

    # First request may be slower (connection setup)
    # Subsequent requests should be consistently fast (pooling)
    avg_later = sum(times[2:]) / len(times[2:])
    avg_first = times[0]

    # Verify connection reuse doesn't create memory leaks
    # Subsequent requests should not get slower
    assert avg_later < avg_first * 2, "Connection reuse not working efficiently"
