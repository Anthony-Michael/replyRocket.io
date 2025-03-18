"""
Database performance testing for ReplyRocket.io.

This script runs performance tests to verify the efficiency of database session 
handling in the application.
"""

import os
import time
import asyncio
import threading
import concurrent.futures
from typing import List, Dict, Any
import statistics
import argparse

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, SessionManager
from app.main import app
from app.utils.db_monitor import get_session_stats, log_active_sessions
from app.models.campaign import EmailCampaign
from app.models.user import User


def run_simple_query(session: Session) -> Dict:
    """Run a simple database query."""
    start_time = time.time()
    result = session.query(User).limit(10).all()
    end_time = time.time()
    
    return {
        "count": len(result),
        "duration": end_time - start_time
    }


def test_session_direct_usage() -> Dict:
    """Test database performance with direct session usage."""
    results = []
    
    for _ in range(50):
        db = SessionLocal()
        try:
            results.append(run_simple_query(db))
        finally:
            db.close()
    
    # Calculate statistics
    durations = [r["duration"] for r in results]
    return {
        "min": min(durations),
        "max": max(durations),
        "avg": statistics.mean(durations),
        "median": statistics.median(durations),
        "std_dev": statistics.stdev(durations),
        "total": sum(durations)
    }


def test_session_context_manager() -> Dict:
    """Test database performance with context manager session usage."""
    results = []
    
    for _ in range(50):
        with SessionManager("test_performance") as db:
            results.append(run_simple_query(db))
    
    # Calculate statistics
    durations = [r["duration"] for r in results]
    return {
        "min": min(durations),
        "max": max(durations),
        "avg": statistics.mean(durations),
        "median": statistics.median(durations),
        "std_dev": statistics.stdev(durations),
        "total": sum(durations)
    }


def test_concurrent_sessions(num_threads: int = 10, queries_per_thread: int = 10) -> Dict:
    """Test database performance with concurrent sessions."""
    results = []
    lock = threading.Lock()
    
    def worker():
        thread_results = []
        for _ in range(queries_per_thread):
            with SessionManager(f"thread_{threading.get_ident()}") as db:
                thread_results.append(run_simple_query(db))
        
        with lock:
            results.extend(thread_results)
    
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Calculate statistics
    durations = [r["duration"] for r in results]
    return {
        "min": min(durations),
        "max": max(durations),
        "avg": statistics.mean(durations),
        "median": statistics.median(durations),
        "std_dev": statistics.stdev(durations),
        "total": sum(durations),
        "thread_count": num_threads,
        "queries_per_thread": queries_per_thread,
        "total_queries": len(results)
    }


def test_api_endpoint_performance(client: TestClient, endpoint: str, iterations: int = 50) -> Dict:
    """Test performance of an API endpoint that uses database sessions."""
    results = []
    
    for _ in range(iterations):
        start_time = time.time()
        response = client.get(endpoint)
        end_time = time.time()
        
        results.append({
            "status_code": response.status_code,
            "duration": end_time - start_time
        })
    
    # Calculate statistics
    durations = [r["duration"] for r in results]
    return {
        "min": min(durations),
        "max": max(durations),
        "avg": statistics.mean(durations),
        "median": statistics.median(durations),
        "std_dev": statistics.stdev(durations),
        "total": sum(durations),
        "success_rate": sum(1 for r in results if r["status_code"] == 200) / len(results)
    }


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a readable string."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.4f} s"


def print_stats(title: str, stats: Dict) -> None:
    """Print formatted statistics."""
    print(f"\n{title}")
    print("-" * 50)
    print(f"Min: {format_duration(stats['min'])}")
    print(f"Max: {format_duration(stats['max'])}")
    print(f"Avg: {format_duration(stats['avg'])}")
    print(f"Median: {format_duration(stats['median'])}")
    print(f"Std Dev: {format_duration(stats['std_dev'])}")
    print(f"Total: {format_duration(stats['total'])}")
    
    if "success_rate" in stats:
        print(f"Success Rate: {stats['success_rate'] * 100:.2f}%")
    
    if "thread_count" in stats:
        print(f"Threads: {stats['thread_count']}")
        print(f"Queries per Thread: {stats['queries_per_thread']}")
        print(f"Total Queries: {stats['total_queries']}")
    
    print("-" * 50)


def main():
    """Run database performance tests."""
    parser = argparse.ArgumentParser(description="Database performance testing")
    parser.add_argument("--api", action="store_true", help="Run API endpoint tests")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads for concurrent tests")
    parser.add_argument("--queries", type=int, default=10, help="Queries per thread")
    args = parser.parse_args()
    
    print("\n=== DATABASE SESSION PERFORMANCE TESTS ===\n")
    
    # 1. Test direct session usage
    direct_stats = test_session_direct_usage()
    print_stats("Direct Session Usage", direct_stats)
    
    # 2. Test session with context manager
    context_stats = test_session_context_manager()
    print_stats("Context Manager Session Usage", context_stats)
    
    # 3. Test concurrent sessions
    concurrent_stats = test_concurrent_sessions(args.threads, args.queries)
    print_stats("Concurrent Session Usage", concurrent_stats)
    
    # 4. Check session monitoring stats
    print("\nSession Monitoring Statistics")
    print("-" * 50)
    stats = get_session_stats()
    for key, value in stats.items():
        if key == "active_by_age":
            print(f"{key}:")
            for age, count in value.items():
                print(f"  {age}: {count}")
        else:
            print(f"{key}: {value}")
    
    # 5. Log any active sessions
    log_active_sessions()
    
    # 6. Test API endpoints if requested
    if args.api:
        print("\n=== API ENDPOINT PERFORMANCE TESTS ===\n")
        client = TestClient(app)
        
        # Test health endpoint (minimal DB usage)
        health_stats = test_api_endpoint_performance(client, "/api/v1/health")
        print_stats("Health Endpoint", health_stats)
        
        # Test campaigns endpoint (more DB usage)
        # Note: This would require authentication in a real scenario
        # campaigns_stats = test_api_endpoint_performance(client, "/api/v1/campaigns")
        # print_stats("Campaigns Endpoint", campaigns_stats)


if __name__ == "__main__":
    main() 