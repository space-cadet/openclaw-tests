#!/usr/bin/env python3
"""
Benchmark results visualizer for model-benchmarks.
Generates comparison plots from results.json.

Usage:
    python3 plot_results.py          # Generate all plots
    python3 plot_results.py --table  # Print comparison table
"""

import json
import sys
from pathlib import Path


def load_results():
    """Load benchmark results from JSON."""
    results_path = Path(__file__).parent / "results.json"
    with open(results_path) as f:
        return json.load(f)


def print_table(results):
    """Print ASCII comparison table."""
    runs = results["runs"]
    
    print("=" * 80)
    print(f"BENCHMARK: {results['benchmark_name']}")
    print(f"TASK: {results['tasks'][0]['name']}")
    print("=" * 80)
    print()
    
    # Header
    print(f"{'Model':<25} {'Provider':<10} {'Score':<8} {'1st Pass':<10} {'Time':<8} {'LoC':<6} {'Self-Corr':<10}")
    print("-" * 80)
    
    for run in runs:
        model = run["model"]
        provider = run["provider"]
        score = f"{run['score']['passed']}/{run['score']['total']}"
        first_pass = f"{run['first_pass_score']['passed']}/{run['first_pass_score']['total']}"
        time = f"{run['runtime_seconds']}s"
        loc = run.get("lines_of_code", "-")
        corrections = run.get("self_correction_events", 0)
        
        print(f"{model:<25} {provider:<10} {score:<8} {first_pass:<10} {time:<8} {loc:<6} {corrections:<10}")
    
    print()
    
    # Efficiency metrics
    print("EFFICIENCY (tokens per test passed):")
    print("-" * 40)
    for run in runs:
        model = run["model"]
        total_tokens = run["tokens"].get("total")
        passed = run["score"]["passed"]
        
        if total_tokens:
            efficiency = total_tokens / passed
            print(f"{model:<25} {efficiency:>8.0f} tokens/test")
        else:
            print(f"{model:<25} {'N/A':>8}")
    
    print()


def generate_markdown_summary(results):
    """Generate markdown summary for README."""
    runs = results["runs"]
    task = results["tasks"][0]
    
    md = f"""# Benchmark Results

## {task['name']}

| Model | Provider | Score | 1st Pass | Time | LoC | Self-Corrections |
|-------|----------|-------|----------|------|-----|------------------|
"""
    
    for run in runs:
        model = run["model"]
        provider = run["provider"]
        score = f"{run['score']['passed']}/{run['score']['total']}"
        first_pass = f"{run['first_pass_score']['passed']}/{run['first_pass_score']['total']}"
        time = f"{run['runtime_seconds']}s"
        loc = run.get("lines_of_code", "-")
        corrections = run.get("self_correction_events", 0)
        
        md += f"| {model} | {provider} | {score} | {first_pass} | {time} | {loc} | {corrections} |\n"
    
    md += "\n### Notes\n\n"
    for run in runs:
        md += f"- **{run['model']}**: {run['notes']}\n"
    
    return md


def plot_results(results):
    """Generate simple ASCII bar chart."""
    runs = results["runs"]
    
    print("SCORE COMPARISON")
    print("=" * 60)
    
    max_score = max(r["score"]["total"] for r in runs)
    
    for run in runs:
        model = run["model"][:20]
        passed = run["score"]["passed"]
        total = run["score"]["total"]
        pct = run["score"]["percentage"]
        
        bar_len = int((passed / max_score) * 40)
        bar = "█" * bar_len
        
        print(f"{model:<20} |{bar:<40}| {passed}/{total} ({pct:.0f}%)")
    
    print()
    
    print("RUNTIME COMPARISON")
    print("=" * 60)
    
    max_time = max(r["runtime_seconds"] for r in runs)
    
    for run in runs:
        model = run["model"][:20]
        time = run["runtime_seconds"]
        
        bar_len = int((time / max_time) * 40)
        bar = "█" * bar_len
        
        print(f"{model:<20} |{bar:<40}| {time}s")
    
    print()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--table":
        results = load_results()
        print_table(results)
    elif len(sys.argv) > 1 and sys.argv[1] == "--markdown":
        results = load_results()
        print(generate_markdown_summary(results))
    else:
        results = load_results()
        plot_results(results)
        print("\nRun with --table for detailed comparison")
        print("Run with --markdown for README-compatible output")


if __name__ == "__main__":
    main()
