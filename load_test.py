"""
EpitopX Load Test — 100 Concurrent Users
Tests: login, profile, proteins, DNA, epitopes
Reports: latency percentiles, success rate, errors
"""

import json
import time
import threading
import statistics
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from collections import defaultdict

BASE_URL = "http://localhost:8000"
NUM_USERS = 100
SHARED_USER = {"username": "testuser", "password": "test1234"}

# ─── Data structures ────────────────────────────────────────────────────────

@dataclass
class Result:
    endpoint: str
    method: str
    status: int
    duration_ms: float
    error: str = ""

results: list[Result] = []
results_lock = threading.Lock()

# ─── HTTP helpers ────────────────────────────────────────────────────────────

def http_post(path: str, data: dict, token: str = "") -> Result:
    url = BASE_URL + path
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Token {token}")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return Result(path, "POST", resp.status, (time.perf_counter() - t0) * 1000)
    except urllib.error.HTTPError as e:
        e.read()
        return Result(path, "POST", e.code, (time.perf_counter() - t0) * 1000, str(e.reason))
    except Exception as e:
        return Result(path, "POST", 0, (time.perf_counter() - t0) * 1000, str(e))


def http_get(path: str, token: str = "") -> Result:
    url = BASE_URL + path
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Token {token}")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return Result(path, "GET", resp.status, (time.perf_counter() - t0) * 1000)
    except urllib.error.HTTPError as e:
        e.read()
        return Result(path, "GET", e.code, (time.perf_counter() - t0) * 1000, str(e.reason))
    except Exception as e:
        return Result(path, "GET", 0, (time.perf_counter() - t0) * 1000, str(e))


# ─── User scenario ───────────────────────────────────────────────────────────

def user_scenario(user_id: int) -> list[Result]:
    """Full user journey: login → profile → proteins → dna → epitopes"""
    user_results = []

    # Step 1: Login
    login_body = json.dumps(SHARED_USER).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/api/users/login/", data=login_body, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.perf_counter()
    token = ""
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            token = data.get("token", "")
            user_results.append(Result("/api/users/login/", "POST", resp.status, (time.perf_counter() - t0) * 1000))
    except urllib.error.HTTPError as e:
        e.read()
        user_results.append(Result("/api/users/login/", "POST", e.code, (time.perf_counter() - t0) * 1000, str(e.reason)))
    except Exception as e:
        user_results.append(Result("/api/users/login/", "POST", 0, (time.perf_counter() - t0) * 1000, str(e)))

    if not token:
        return user_results  # Can't continue without token

    # Steps 2–5: Authenticated requests
    user_results.append(http_get("/api/users/profile/", token))
    user_results.append(http_get("/api/proteins/", token))
    user_results.append(http_get("/api/dna/", token))
    user_results.append(http_get("/api/epitopes/", token))

    return user_results


# ─── Reporting ───────────────────────────────────────────────────────────────

def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def print_report(all_results: list[Result], total_time: float):
    print("\n" + "=" * 65)
    print("  EPITOPX LOAD TEST REPORT — 100 Concurrent Users")
    print("=" * 65)
    print(f"  Total wall time: {total_time:.2f}s | Total requests: {len(all_results)}")
    print("=" * 65)

    by_endpoint: dict[str, list[Result]] = defaultdict(list)
    for r in all_results:
        by_endpoint[r.endpoint].append(r)

    grand_ok = grand_fail = 0
    all_durations = []
    error_details = defaultdict(int)

    for endpoint, rs in sorted(by_endpoint.items()):
        durations = [r.duration_ms for r in rs]
        ok = sum(1 for r in rs if 200 <= r.status < 300)
        fail = len(rs) - ok
        grand_ok += ok
        grand_fail += fail
        all_durations.extend(durations)

        for r in rs:
            if r.error:
                error_details[f"{r.endpoint} [{r.status}] {r.error}"] += 1

        print(f"\n  {endpoint}")
        print(f"    Requests : {len(rs)} | OK: {ok} | FAIL: {fail}")
        if durations:
            print(f"    Latency  : avg={statistics.mean(durations):.0f}ms  "
                  f"p50={percentile(durations, 50):.0f}ms  "
                  f"p90={percentile(durations, 90):.0f}ms  "
                  f"p99={percentile(durations, 99):.0f}ms  "
                  f"max={max(durations):.0f}ms")

    print("\n" + "-" * 65)
    total = grand_ok + grand_fail
    rate = (grand_ok / total * 100) if total else 0
    print(f"  OVERALL  Total={total} | Success={grand_ok} ({rate:.1f}%) | Fail={grand_fail}")
    if all_durations:
        print(f"  LATENCY  avg={statistics.mean(all_durations):.0f}ms  "
              f"p50={percentile(all_durations,50):.0f}ms  "
              f"p90={percentile(all_durations,90):.0f}ms  "
              f"p99={percentile(all_durations,99):.0f}ms")
    rps = total / total_time if total_time > 0 else 0
    print(f"  THROUGHPUT {rps:.1f} req/s")

    if error_details:
        print("\n  ERRORS:")
        for msg, count in sorted(error_details.items(), key=lambda x: -x[1]):
            print(f"    [{count}x] {msg}")

    print("=" * 65 + "\n")
    return grand_ok, grand_fail


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nStarting load test: {NUM_USERS} concurrent users against {BASE_URL}")
    print("Each user runs: login -> profile -> proteins -> dna -> epitopes")
    print("Launching all users simultaneously...\n")

    all_results: list[Result] = []
    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=NUM_USERS) as executor:
        futures = {executor.submit(user_scenario, i): i for i in range(NUM_USERS)}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            user_results = future.result()
            all_results.extend(user_results)
            if completed % 20 == 0:
                print(f"  Progress: {completed}/{NUM_USERS} users done...")

    wall_time = time.perf_counter() - wall_start
    ok, fail = print_report(all_results, wall_time)

    # Exit code: 0 if success rate >= 95%, else 1
    success_rate = ok / (ok + fail) * 100 if (ok + fail) else 0
    exit(0 if success_rate >= 95 else 1)
