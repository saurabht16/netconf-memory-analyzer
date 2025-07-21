#!/usr/bin/env python3
"""
Comprehensive Report Generator and Analyzer
Demonstrates the full capabilities of the Memory Leak Analyzer
"""

import subprocess
import time
from pathlib import Path
import csv

def generate_reports():
    print("🚀 COMPREHENSIVE MEMORY LEAK ANALYSIS DEMONSTRATION")
    print("=" * 80)
    
    # Generate Valgrind analysis
    print("\n📊 VALGRIND COMPREHENSIVE ANALYSIS")
    print("-" * 50)
    
    valgrind_cmd = [
        "python", "memory_leak_analyzer_enhanced.py",
        "--input", "sample_data/comprehensive_valgrind.xml",
        "--cleanup",
        "--impact-analysis", 
        "--trend-analysis",
        "--version", "v2.0.0-comprehensive",
        "--export-csv", "final_valgrind_report.csv",
        "--output", "final_valgrind_report.html"
    ]
    
    result1 = subprocess.run(valgrind_cmd, capture_output=True, text=True)
    print("Command:", " ".join(valgrind_cmd))
    print("\nOutput:")
    print(result1.stdout)
    if result1.stderr:
        print("Errors:", result1.stderr)
    
    time.sleep(1)
    
    # Generate ASan analysis  
    print("\n🔍 ASAN COMPREHENSIVE ANALYSIS")
    print("-" * 50)
    
    asan_cmd = [
        "python", "memory_leak_analyzer_enhanced.py", 
        "--input", "sample_data/comprehensive_asan.log",
        "--cleanup",
        "--impact-analysis",
        "--export-csv", "final_asan_report.csv", 
        "--output", "final_asan_report.html"
    ]
    
    result2 = subprocess.run(asan_cmd, capture_output=True, text=True)
    print("Command:", " ".join(asan_cmd))
    print("\nOutput:")
    print(result2.stdout)
    if result2.stderr:
        print("Errors:", result2.stderr)

def analyze_generated_files():
    print("\n\n📁 GENERATED FILES ANALYSIS")
    print("=" * 80)
    
    files_to_check = [
        "final_valgrind_report.html",
        "final_valgrind_report.csv", 
        "final_asan_report.html",
        "final_asan_report.csv"
    ]
    
    for filename in files_to_check:
        file_path = Path(filename)
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {filename}: {size:,} bytes")
            
            if filename.endswith('.csv'):
                analyze_csv_report(filename)
            elif filename.endswith('.html'):
                analyze_html_report(filename)
        else:
            print(f"❌ {filename}: Not found")

def analyze_csv_report(filename):
    """Analyze CSV report contents"""
    print(f"\n📄 CSV Report Analysis: {filename}")
    print("-" * 40)
    
    try:
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        print(f"  Total leaks: {len(rows)}")
        
        # Analyze by severity
        severity_counts = {}
        total_bytes = 0
        leak_types = {}
        files_affected = set()
        
        for row in rows:
            severity = row.get('severity', 'Unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            try:
                total_bytes += int(row.get('size_bytes', 0))
            except (ValueError, TypeError):
                pass
            
            leak_type = row.get('leak_type', 'Unknown')
            leak_types[leak_type] = leak_types.get(leak_type, 0) + 1
            
            # Extract file from stack trace or location
            location = row.get('primary_location', '')
            if '(' in location and ')' in location:
                file_part = location.split('(')[1].split(')')[0]
                if ':' in file_part:
                    file_name = file_part.split(':')[0]
                    if file_name and not file_name.startswith('/usr/'):
                        files_affected.add(file_name)
        
        print(f"  Total memory leaked: {total_bytes:,} bytes")
        print(f"  Files affected: {len(files_affected)}")
        
        print(f"  Severity breakdown:")
        for severity, count in severity_counts.items():
            print(f"    {severity}: {count}")
        
        print(f"  Leak types:")
        for leak_type, count in leak_types.items():
            print(f"    {leak_type}: {count}")
            
        if files_affected:
            print(f"  Key files with issues:")
            for file_name in sorted(list(files_affected)[:5]):
                print(f"    {file_name}")
                
    except Exception as e:
        print(f"  Error analyzing CSV: {e}")

def analyze_html_report(filename):
    """Analyze HTML report contents"""
    print(f"\n🌐 HTML Report Analysis: {filename}")
    print("-" * 40)
    
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        # Check for key features
        features = [
            ("📊 Charts/Visualizations", "Chart.js" in content or "canvas" in content),
            ("🔍 Client-side Filtering", "function filterLeaks" in content),
            ("📈 Statistical Summary", "statistics-container" in content),
            ("🎯 Impact Analysis", "impact-" in content or "priority" in content),
            ("📱 Responsive Design", "viewport" in content and "responsive" in content),
            ("🎨 Modern Styling", "CSS" in content and "style" in content),
            ("⚡ Interactive Features", "onclick" in content or "addEventListener" in content),
            ("📋 Detailed Stack Traces", "stack-trace" in content)
        ]
        
        print(f"  File size: {len(content):,} characters")
        print(f"  Features detected:")
        
        for feature_name, detected in features:
            status = "✅" if detected else "❌"
            print(f"    {status} {feature_name}")
        
        # Count key elements
        leak_count = content.count('leak-item') or content.count('leak-entry')
        chart_count = content.count('<canvas')
        
        print(f"  Estimated leak entries: {leak_count}")
        print(f"  Chart elements: {chart_count}")
        
    except Exception as e:
        print(f"  Error analyzing HTML: {e}")

def show_trend_analysis():
    print("\n\n📈 TREND ANALYSIS DEMONSTRATION")
    print("=" * 80)
    
    # Export current trends
    trend_cmd = ["python", "memory_leak_analyzer.py", "--export-trends-csv", "final_trends.csv"]
    result = subprocess.run(trend_cmd, capture_output=True, text=True)
    
    print("Trend export command:", " ".join(trend_cmd))
    print("Result:", result.stdout.strip())
    
    if Path("final_trends.csv").exists():
        print("\n📊 Trend Data Summary:")
        with open("final_trends.csv", 'r') as f:
            lines = f.readlines()
            print(f"  Data points: {len(lines) - 1}")  # Minus header
            print(f"  Sample data:")
            for i, line in enumerate(lines[:5]):
                print(f"    {i+1}: {line.strip()}")

def show_usage_examples():
    print("\n\n💡 USAGE EXAMPLES FOR GENERATED REPORTS")
    print("=" * 80)
    
    examples = [
        ("Development Team", "Use HTML reports for interactive leak investigation and prioritization"),
        ("QA Process", "Import CSV data into testing dashboards for trend monitoring"),
        ("CI/CD Pipeline", "Automate quality gates based on leak counts and severity"),
        ("Management", "Generate executive summaries from trend data"),
        ("Performance Analysis", "Track memory usage patterns across releases"),
        ("Code Review", "Focus reviews on files with high-impact leaks"),
        ("Debugging", "Use detailed stack traces to identify root causes"),
        ("Release Planning", "Assess memory leak debt before releases")
    ]
    
    for use_case, description in examples:
        print(f"🎯 {use_case:15}: {description}")

def main():
    print("Starting comprehensive report generation...")
    
    # Generate all reports
    generate_reports()
    
    # Analyze the generated files
    analyze_generated_files()
    
    # Show trend analysis
    show_trend_analysis()
    
    # Show usage examples
    show_usage_examples()
    
    print("\n" + "=" * 80)
    print("🎉 COMPREHENSIVE ANALYSIS COMPLETED!")
    print("=" * 80)
    print("\n📁 Generated Files:")
    print("  • final_valgrind_report.html - Interactive Valgrind analysis")
    print("  • final_valgrind_report.csv  - Detailed Valgrind data") 
    print("  • final_asan_report.html     - Interactive ASan analysis")
    print("  • final_asan_report.csv      - Detailed ASan data")
    print("  • final_trends.csv           - Historical trend data")
    print("\n🚀 Ready for enterprise deployment and analysis!")

if __name__ == "__main__":
    main() 