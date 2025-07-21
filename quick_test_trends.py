#!/usr/bin/env python3
"""
Quick test for trend export functionality
"""

import subprocess
import time
from pathlib import Path

def test_trend_export():
    print("🧪 Testing Trend Export Functionality")
    print("=" * 50)
    
    # Step 1: Create baseline
    print("1. Creating baseline...")
    result1 = subprocess.run([
        "python", "memory_leak_analyzer_enhanced.py",
        "--input", "sample_data/sample_valgrind.xml",
        "--baseline", "--version", "test-v1.0"
    ], capture_output=True, text=True)
    
    if result1.returncode == 0:
        print("✅ Baseline created successfully")
        print(result1.stdout.strip())
    else:
        print("❌ Baseline creation failed")
        print(result1.stderr)
        return
    
    time.sleep(1)
    
    # Step 2: Add another data point
    print("\n2. Adding second data point...")
    result2 = subprocess.run([
        "python", "memory_leak_analyzer_enhanced.py", 
        "--input", "sample_data/sample_noisy_valgrind.xml",
        "--trend-analysis", "--version", "test-v1.1"
    ], capture_output=True, text=True)
    
    if result2.returncode == 0:
        print("✅ Second data point added")
        # Print only the trend analysis part
        lines = result2.stdout.split('\n')
        for line in lines:
            if 'TREND ANALYSIS' in line or 'Previous:' in line or 'Current:' in line or 'Change:' in line:
                print(line)
    else:
        print("❌ Second data point failed")
        print(result2.stderr)
        return
    
    time.sleep(1)
    
    # Step 3: Export trends to CSV
    print("\n3. Exporting trends to CSV...")
    result3 = subprocess.run([
        "python", "memory_leak_analyzer.py",
        "--export-trends-csv", "test_export.csv"
    ], capture_output=True, text=True)
    
    if result3.returncode == 0:
        print("✅ Trend export completed")
        print(result3.stdout.strip())
        
        # Check if file was created
        csv_file = Path("test_export.csv")
        if csv_file.exists():
            print(f"✅ CSV file created: {csv_file.stat().st_size} bytes")
            
            # Show first few lines
            with open(csv_file, 'r') as f:
                lines = f.readlines()[:5]
                print("\n📄 CSV Contents (first 5 lines):")
                for i, line in enumerate(lines, 1):
                    print(f"  {i}: {line.strip()}")
        else:
            print("❌ CSV file was not created")
    else:
        print("❌ Trend export failed")
        print(result3.stderr)
    
    print("\n" + "=" * 50)
    print("✅ Trend export test completed!")

if __name__ == "__main__":
    test_trend_export() 