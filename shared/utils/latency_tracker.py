"""
shared/utils/latency_tracker.py — Pipeline latency instrumentation.

Purpose:
    Measures wall-clock duration for each pipeline stage. Used for
    performance monitoring and usage_records cost estimation.

Usage:
    tracker = LatencyTracker()
    with tracker.measure("STT"):
        result = stt_provider.transcribe(...)
    print(tracker.all())  # {"STT": 0.842, ...}

Methods:
    measure(label) — context manager that times a block
    get(label) → float
    all() → dict[str, float]
    total() → float
"""
