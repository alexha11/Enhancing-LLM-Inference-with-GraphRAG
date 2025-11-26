"""Performance Benchmarking for GraphRAG Pipeline.

This module provides timing instrumentation and visualization for measuring
performance of each stage in the GraphRAG pipeline.
"""

import time
from collections import defaultdict
from typing import Any, Callable, Optional, Dict, List
from contextlib import contextmanager
import json


class PerformanceTracker:
    """Tracks performance metrics for pipeline stages."""

    def __init__(self):
        """Initialize performance tracker."""
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.current_run: Dict[str, float] = {}
        self.stage_stack: List[tuple] = []

    @contextmanager
    def track_stage(self, stage_name: str):
        """Context manager to track execution time of a stage.
        
        Usage:
            with tracker.track_stage("schema_retrieval"):
                # code to measure
                
        Args:
            stage_name: Name of the pipeline stage
        """
        start_time = time.perf_counter()
        self.stage_stack.append((stage_name, start_time))
        try:
            yield
        finally:
            end_time = time.perf_counter()
            elapsed = end_time - start_time
            
            # Pop from stack
            self.stage_stack.pop()
            
            # Record timing
            self.timings[stage_name].append(elapsed)
            self.current_run[stage_name] = elapsed

    def get_current_run(self) -> Dict[str, float]:
        """Get timings for the current run.
        
        Returns:
            Dictionary mapping stage names to elapsed time in seconds
        """
        return self.current_run.copy()

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get aggregated statistics for all stages.
        
        Returns:
            Dictionary with statistics (mean, min, max, total) for each stage
        """
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
        """Get timing breakdown with percentages for latest run.
        
        Returns:
            Dictionary with stage timings and percentages
        """
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
        """Reset all timing data."""
        self.timings.clear()
        self.current_run.clear()
        self.stage_stack.clear()

    def print_summary(self):
        """Print a formatted summary of performance metrics."""
        print("\n" + "="*60)
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
        """Generate flamegraph-compatible data.
        
        Returns:
            Flamegraph data in folded stack format
        """
        # Simple flamegraph format: stack;trace elapsed_time
        lines = []
        for stage, times in self.timings.items():
            for elapsed in times:
                # Convert to microseconds (integer)
                microseconds = int(elapsed * 1_000_000)
                lines.append(f"pipeline;{stage} {microseconds}")
        
        return "\n".join(lines)

    def export_to_json(self, filepath: str):
        """Export performance data to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        data = {
            "statistics": self.get_statistics(),
            "latest_run": self.get_timing_breakdown(),
            "all_timings": {k: list(v) for k, v in self.timings.items()},
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def create_text_visualization(breakdown: Dict[str, Any], width: int = 50) -> str:
    """Create a simple text-based bar chart visualization.
    
    Args:
        breakdown: Timing breakdown from PerformanceTracker
        width: Width of the bar chart
        
    Returns:
        Formatted string with visualization
    """
    if not breakdown or "_total" not in breakdown:
        return "No data to visualize"
    
    lines = ["\n" + "="*70]
    lines.append("PERFORMANCE VISUALIZATION")
    lines.append("="*70 + "\n")
    
    # Sort by time descending, exclude _total
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


# Decorator for timing functions
def timed_stage(stage_name: str, tracker: PerformanceTracker):
    """Decorator to automatically track function execution time.
    
    Args:
        stage_name: Name of the stage
        tracker: PerformanceTracker instance
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with tracker.track_stage(stage_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
