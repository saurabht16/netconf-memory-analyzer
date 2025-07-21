#!/usr/bin/env python3
"""
Test script for Memory Leak Analyzer cleanup functionality
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    print(f"\n{'='*60}")
    print(f"🧹 {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Stderr:", result.stderr)

def main():
    print("🧹 MEMORY LEAK ANALYZER - CLEANUP FUNCTIONALITY TEST")
    print("=" * 80)
    
    # Test basic functionality without cleanup
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml",
        "1. Basic analysis (no cleanup)"
    )
    
    # Test with cleanup enabled
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup",
        "2. With cleanup enabled (removes system libs, small leaks)"
    )
    
    # Test keeping system libraries
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup --keep-system-libs",
        "3. Cleanup but keep system libraries"
    )
    
    # Test custom minimum leak size
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup --min-leak-size 50",
        "4. Cleanup with minimum leak size of 50 bytes"
    )
    
    # Test with grouping
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup --group-similar",
        "5. Cleanup with similar leak grouping"
    )
    
    # Test ASan cleanup
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_asan.log --cleanup",
        "6. ASan log cleanup"
    )
    
    # Test custom exclude pattern
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup --exclude-pattern 'stdlib'",
        "7. Cleanup with custom exclude pattern 'stdlib'"
    )
    
    # Combined cleanup, filters, and grouping
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup --filter-severity HIGH --group-similar",
        "8. Combined: cleanup + HIGH severity filter + grouping"
    )
    
    # Generate cleaned HTML report
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --cleanup --output cleaned_report.html",
        "9. Generate cleaned HTML report"
    )
    
    print("\n" + "=" * 80)
    print("🧹 CLEANUP FUNCTIONALITY TEST COMPLETED!")
    print("\nCleanup Features:")
    print("  ✅ Remove system library leaks (libc, libpthread, etc.)")
    print("  ✅ Remove third-party library leaks (Qt, boost, etc.)")
    print("  ✅ Filter out small leaks (configurable minimum size)")
    print("  ✅ Remove incomplete stack traces")
    print("  ✅ Optionally remove still-reachable memory")
    print("  ✅ Custom exclude patterns")
    print("  ✅ Group similar leak patterns")
    print("  ✅ Skip suppressed Valgrind errors")
    print("  ✅ Cleanup statistics and reporting")
    print("\nCleanup Options:")
    print("  --cleanup              : Enable cleanup")
    print("  --keep-system-libs     : Keep system library leaks")
    print("  --keep-third-party     : Keep third-party library leaks")
    print("  --keep-reachable       : Keep still-reachable memory")
    print("  --min-leak-size N      : Minimum leak size (default: 8 bytes)")
    print("  --exclude-pattern P    : Additional exclude pattern")
    print("  --group-similar        : Group similar leaks")
    print("=" * 80)

if __name__ == "__main__":
    main() 