#!/usr/bin/env python3
"""
Demonstration script for Memory Leak Analyzer filtering capabilities
"""

import subprocess
import time

def run_command(cmd, description):
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    print("-" * 60)
    
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Stderr:", result.stderr)
    
    time.sleep(1)

def main():
    print("=" * 80)
    print("MEMORY LEAK ANALYZER - FILTERING CAPABILITIES DEMO")
    print("=" * 80)
    
    # Basic analysis
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml",
        "1. Basic analysis without filters"
    )
    
    # Filter by severity
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --filter-severity HIGH",
        "2. Filter by HIGH severity only"
    )
    
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --filter-severity LOW",
        "3. Filter by LOW severity only"
    )
    
    # Filter by file
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --filter-file test.c",
        "4. Filter by file name pattern 'test.c'"
    )
    
    # Filter by function
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --filter-function main",
        "5. Filter by function name 'main'"
    )
    
    # Size range filtering
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --min-size 50 --max-size 100",
        "6. Filter by size range (50-100 bytes)"
    )
    
    # Search functionality
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_asan.log --search malloc",
        "7. Search for 'malloc' in ASan log"
    )
    
    # Combined filters
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --filter-function main --filter-severity HIGH",
        "8. Combined filter: function='main' AND severity='HIGH'"
    )
    
    print("\n" + "=" * 80)
    print("FILTERING DEMO COMPLETED!")
    print("\nAvailable filter options:")
    print("  --filter-file      : Filter by file name pattern")
    print("  --filter-dir       : Filter by directory pattern") 
    print("  --filter-function  : Filter by function name pattern")
    print("  --filter-severity  : Filter by severity (HIGH/MEDIUM/LOW)")
    print("  --min-size         : Minimum leak size in bytes")
    print("  --max-size         : Maximum leak size in bytes")
    print("  --search           : Search term in any field")
    print("\nGUI Mode: python memory_leak_analyzer.py --gui")
    print("HTML reports now include interactive client-side filtering!")
    print("=" * 80)

if __name__ == "__main__":
    main() 