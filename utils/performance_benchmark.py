"""
Benchmarking pipeline latency
Timing breakdowns
Visualization
Optional flamegraph output
Memory tracking
"""

import time
from collections import defaultdict
from typing import Any, Callable, Dict, List
from contextlib import contextmanager
import json
import psutil
import os


class PerformanceTracker:
    def __init__(self, track_memory: bool = True):
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.current_run: Dict[str, float] = {}
        self.stage_stack: List[tuple] = []
        self.track_memory = track_memory
        self.memory_usage: Dict[str, List[float]] = defaultdict(list) if track_memory else None
        self.process = psutil.Process(os.getpid()) if track_memory else None

    @contextmanager
    def track_stage(self, stage_name: str):
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / 1024 / 1024 if self.track_memory else 0  # MB
        
        self.stage_stack.append((stage_name, start_time))
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss / 1024 / 1024 if self.track_memory else 0  # MB
            elapsed = end_time - start_time
            memory_delta = end_memory - start_memory if self.track_memory else 0
            
            self.stage_stack.pop()
            
            self.timings[stage_name].append(elapsed)
            self.current_run[stage_name] = elapsed
            
            if self.track_memory and self.memory_usage is not None:
                self.memory_usage[stage_name].append(memory_delta)

    def get_current_run(self) -> Dict[str, float]:
        return self.current_run.copy()

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        stats = {}
        for stage, times in self.timings.items():
            if times:
                stats[stage] = {
                    "count": len(times),
                    "mean": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "total": sum(times),
                }
        return stats

    def get_timing_breakdown(self) -> Dict[str, Any]:
        if not self.current_run:
            return {}
        
        total_time = sum(self.current_run.values())
        breakdown = {}
        
        for stage, elapsed in sorted(self.current_run.items(), key=lambda x: x[1], reverse=True):
            percentage = (elapsed / total_time * 100) if total_time > 0 else 0
            breakdown[stage] = {
                "time_seconds": elapsed,
                "time_ms": elapsed * 1000,
                "percentage": percentage,
            }
        
        breakdown["_total"] = {
            "time_seconds": total_time,
            "time_ms": total_time * 1000,
            "percentage": 100.0,
        }
        
        return breakdown

    def reset(self):
        self.timings.clear()
        self.current_run.clear()
        self.stage_stack.clear()
        if self.memory_usage is not None:
            self.memory_usage.clear()

    def print_summary(self):
        print(("\n" + "="*60))
        print("PERFORMANCE SUMMARY")
        print("="*60)
        
        breakdown = self.get_timing_breakdown()
        if not breakdown:
            print("No timing data available.")
            return
        
        print(f"\n{'Stage':<30} {'Time (ms)':<12} {'%':<8}")
        print("-"*60)
        
        for stage, metrics in breakdown.items():
            if stage == "_total":
                print("-"*60)
                print(f"{'TOTAL':<30} {metrics['time_ms']:<12.2f} {metrics['percentage']:<8.1f}")
            else:
                print(f"{stage:<30} {metrics['time_ms']:<12.2f} {metrics['percentage']:<8.1f}")
        
        print("="*60 + "\n")

    def generate_flamegraph_data(self) -> str:
        lines = []
        for stage, times in self.timings.items():
            for elapsed in times:
                microseconds = int(elapsed * 1_000_000)
                lines.append(f"pipeline;{stage} {microseconds}")
        
        return "\n".join(lines)

    def get_memory_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get memory usage statistics."""
        if not self.track_memory or not self.memory_usage:
            return {}
        
        stats = {}
        for stage, memory_deltas in self.memory_usage.items():
            if memory_deltas:
                stats[stage] = {
                    "count": len(memory_deltas),
                    "mean_mb": sum(memory_deltas) / len(memory_deltas),
                    "min_mb": min(memory_deltas),
                    "max_mb": max(memory_deltas),
                    "total_mb": sum(memory_deltas),
                }
        return stats

    def export_to_dataframe(self):
        """Export timing data to pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for DataFrame export")
        
        data = []
        for stage, times in self.timings.items():
            for i, elapsed in enumerate(times):
                row = {
                    'stage': stage,
                    'run_number': i + 1,
                    'time_seconds': elapsed,
                    'time_ms': elapsed * 1000,
                }
                if self.track_memory and stage in self.memory_usage:
                    row['memory_delta_mb'] = self.memory_usage[stage][i] if i < len(self.memory_usage[stage]) else 0
                data.append(row)
        
        return pd.DataFrame(data)

    def export_to_json(self, filepath: str):
        data = {
            "statistics": self.get_statistics(),
            "latest_run": self.get_timing_breakdown(),
            "all_timings": {k: list(v) for k, v in self.timings.items()},
        }
        
        if self.track_memory:
            data["memory_statistics"] = self.get_memory_statistics()
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def create_text_visualization(breakdown: Dict[str, Any], width: int = 50) -> str:
    if not breakdown or "_total" not in breakdown:
        return "No data to visualize"
    
    lines = ["\n" + "="*70]
    lines.append("PERFORMANCE VISUALIZATION")
    lines.append("="*70 + "\n")
    
    stages = [(k, v) for k, v in breakdown.items() if k != "_total"]
    stages.sort(key=lambda x: x[1]["time_seconds"], reverse=True)
    
    for stage, metrics in stages:
        bar_length = int(metrics["percentage"] / 100 * width)
        bar = "█" * bar_length
        lines.append(f"{stage:<25} |{bar:<{width}}| {metrics['time_ms']:>8.2f}ms ({metrics['percentage']:>5.1f}%)")
    
    total = breakdown["_total"]
    lines.append("-"*70)
    lines.append(f"{'TOTAL':<25} {'':<{width+2}} {total['time_ms']:>8.2f}ms")
    lines.append("="*70 + "\n")
    
    return "\n".join(lines)


def timed_stage(stage_name: str, tracker: PerformanceTracker):
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with tracker.track_stage(stage_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
