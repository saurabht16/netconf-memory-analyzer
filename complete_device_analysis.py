#!/usr/bin/env python3
"""
Complete Device Memory Analysis Workflow
1. Run containerized device tests
2. Parse downloaded logs (Valgrind XML / ASan)  
3. Generate HTML and CSV reports
4. Open results in browser
"""

import argparse
import subprocess
import sys
from pathlib import Path
import json
import webbrowser
from datetime import datetime

def run_device_testing(config_file: Path, device_name: str = None):
    """Step 1: Run device testing and download logs"""
    print("🚀 STEP 1: RUNNING DEVICE MEMORY TESTING")
    print("=" * 60)
    
    cmd = ["python", "parallel_device_tester.py", "--config", str(config_file)]
    if device_name:
        cmd.extend(["--device", device_name])
    
    print(f"💻 Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            print("✅ Device testing completed successfully")
            print("📁 Log files downloaded to local machine")
            return True
        else:
            print(f"❌ Device testing failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Device testing timed out (1 hour limit)")
        return False
    except Exception as e:
        print(f"❌ Device testing error: {e}")
        return False

def find_downloaded_logs(results_dir: Path) -> list:
    """Step 2: Find downloaded Valgrind XML and ASan log files"""
    print("\n🔍 STEP 2: FINDING DOWNLOADED LOG FILES")
    print("=" * 60)
    
    log_files = []
    
    # Find Valgrind XML files
    valgrind_files = list(results_dir.rglob("*.xml"))
    for file in valgrind_files:
        if file.stat().st_size > 0:  # Non-empty files
            log_files.append({"file": file, "type": "valgrind"})
            print(f"📄 Found Valgrind log: {file}")
    
    # Find ASan log files  
    asan_files = list(results_dir.rglob("*.log"))
    for file in asan_files:
        if file.stat().st_size > 0 and "asan" in file.name.lower():
            log_files.append({"file": file, "type": "asan"})
            print(f"📄 Found ASan log: {file}")
    
    print(f"\n✅ Found {len(log_files)} log files to analyze")
    return log_files

def analyze_logs_and_generate_reports(log_files: list, output_dir: Path):
    """Step 3: Analyze logs and generate HTML/CSV reports"""
    print("\n📊 STEP 3: ANALYZING LOGS AND GENERATING REPORTS")
    print("=" * 60)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_reports = []
    
    for log_info in log_files:
        log_file = log_info["file"]
        log_type = log_info["type"]
        
        print(f"\n🔬 Analyzing {log_type.upper()} log: {log_file.name}")
        
        # Generate base filename
        base_name = log_file.stem
        html_output = output_dir / f"{base_name}_report.html"
        csv_output = output_dir / f"{base_name}_analysis.csv"
        
        # Build analysis command
        cmd = [
            "python", "memory_leak_analyzer_enhanced.py",
            "--input", str(log_file),
            "--output", str(html_output),
            "--type", log_type,
            "--cleanup",                    # Remove noise
            "--impact-analysis",            # Calculate impact scores
            "--trend-analysis",             # Historical tracking
            "--group-similar",              # Group similar leaks
            "--export-csv", str(csv_output) # Export CSV
        ]
        
        print(f"💻 Executing: python memory_leak_analyzer_enhanced.py ...")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Generated HTML report: {html_output}")
                print(f"✅ Generated CSV report: {csv_output}")
                
                generated_reports.append({
                    "log_file": str(log_file),
                    "log_type": log_type,
                    "html_report": str(html_output),
                    "csv_report": str(csv_output),
                    "analysis_summary": _extract_analysis_summary(result.stdout)
                })
            else:
                print(f"❌ Analysis failed for {log_file}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Analysis timed out for {log_file}")
        except Exception as e:
            print(f"❌ Analysis error for {log_file}: {e}")
    
    return generated_reports

def _extract_analysis_summary(stdout: str) -> dict:
    """Extract key metrics from analysis output"""
    summary = {}
    
    try:
        lines = stdout.split('\n')
        for line in lines:
            if 'Total Leaks Analyzed:' in line:
                summary['total_leaks'] = line.split(':')[1].strip()
            elif 'Average Impact Score:' in line:
                summary['avg_impact'] = line.split(':')[1].strip()
            elif 'HIGH' in line and '%' in line:
                summary['high_priority'] = line.split(':')[1].strip()
    except:
        pass
    
    return summary

def generate_consolidated_report(reports: list, output_dir: Path):
    """Step 4: Generate consolidated summary report"""
    print("\n📋 STEP 4: GENERATING CONSOLIDATED REPORT")
    print("=" * 60)
    
    consolidated_file = output_dir / "consolidated_analysis_report.html"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Consolidated Memory Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f8ff; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .report-link {{ display: inline-block; background: #4CAF50; color: white; 
                       padding: 10px 15px; text-decoration: none; border-radius: 3px; margin: 5px; }}
        .report-link:hover {{ background: #45a049; }}
        .metrics {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .metric {{ background: white; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🐳 Containerized Device Memory Analysis Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Reports: {len(reports)}</p>
    </div>
    
    <h2>📊 Analysis Summary</h2>
    <div class="metrics">
"""
    
    total_leaks = 0
    high_priority_reports = 0
    
    for report in reports:
        summary = report.get('analysis_summary', {})
        
        # Extract numbers for totals
        try:
            leaks = int(summary.get('total_leaks', '0'))
            total_leaks += leaks
        except:
            pass
        
        if 'high_priority' in summary:
            high_priority_reports += 1
        
        html_content += f"""
        <div class="metric">
            <h4>{Path(report['log_file']).stem}</h4>
            <p><strong>Type:</strong> {report['log_type'].upper()}</p>
            <p><strong>Leaks:</strong> {summary.get('total_leaks', 'N/A')}</p>
            <p><strong>Avg Impact:</strong> {summary.get('avg_impact', 'N/A')}</p>
            <p><strong>High Priority:</strong> {summary.get('high_priority', 'N/A')}</p>
        </div>
"""
    
    html_content += f"""
    </div>
    
    <div class="summary">
        <h3>🎯 Overall Statistics</h3>
        <p><strong>Total Memory Leaks Found:</strong> {total_leaks}</p>
        <p><strong>Reports with High Priority Issues:</strong> {high_priority_reports}/{len(reports)}</p>
        <p><strong>Analysis Coverage:</strong> {len(reports)} containers/processes tested</p>
    </div>
    
    <h2>📄 Individual Reports</h2>
"""
    
    for report in reports:
        html_file = Path(report['html_report'])
        csv_file = Path(report['csv_report'])
        
        html_content += f"""
    <div class="summary">
        <h4>🔬 {Path(report['log_file']).stem} ({report['log_type'].upper()})</h4>
        <p><strong>Source Log:</strong> {report['log_file']}</p>
        <a href="{html_file.name}" class="report-link">📊 View HTML Report</a>
        <a href="{csv_file.name}" class="report-link">📈 Download CSV</a>
    </div>
"""
    
    html_content += """
    
    <div class="summary">
        <h3>🛠️ Next Steps</h3>
        <ul>
            <li>Review individual HTML reports for detailed leak analysis</li>
            <li>Use CSV files for tracking and trend analysis</li>
            <li>Prioritize fixing HIGH impact leaks first</li>
            <li>Set up automated monitoring for memory growth</li>
        </ul>
    </div>
    
</body>
</html>
"""
    
    with open(consolidated_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Consolidated report: {consolidated_file}")
    return consolidated_file

def open_reports_in_browser(consolidated_report: Path):
    """Step 5: Open reports in web browser"""
    print("\n🌐 STEP 5: OPENING REPORTS IN BROWSER")
    print("=" * 60)
    
    try:
        webbrowser.open(f"file://{consolidated_report.absolute()}")
        print(f"✅ Opened consolidated report in browser")
        print(f"📂 Report location: {consolidated_report}")
    except Exception as e:
        print(f"❌ Could not open browser: {e}")
        print(f"📂 Manually open: {consolidated_report}")

def main():
    parser = argparse.ArgumentParser(description='Complete Device Memory Analysis Workflow')
    
    parser.add_argument('--config', '-c', type=Path, required=True,
                       help='Device configuration file')
    parser.add_argument('--device', '-d', 
                       help='Specific device to test (optional)')
    parser.add_argument('--output-dir', type=Path, default=Path('analysis_reports'),
                       help='Output directory for reports (default: analysis_reports)')
    parser.add_argument('--skip-testing', action='store_true',
                       help='Skip device testing, only analyze existing logs')
    parser.add_argument('--results-dir', type=Path, default=Path('results'),
                       help='Directory containing downloaded logs (default: results)')
    parser.add_argument('--open-browser', action='store_true', default=True,
                       help='Open reports in browser when complete')
    
    args = parser.parse_args()
    
    print("🔬 COMPLETE DEVICE MEMORY ANALYSIS WORKFLOW")
    print("=" * 80)
    print("This tool will:")
    print("1. 🚀 Run containerized device testing")
    print("2. 🔍 Find downloaded Valgrind/ASan logs") 
    print("3. 📊 Analyze logs with impact scoring")
    print("4. 📄 Generate HTML and CSV reports")
    print("5. 🌐 Open results in browser")
    print()
    
    # Step 1: Device Testing (if not skipped)
    if not args.skip_testing:
        success = run_device_testing(args.config, args.device)
        if not success:
            print("❌ Device testing failed. Exiting.")
            return 1
    else:
        print("⏭️  Skipping device testing (using existing logs)")
    
    # Step 2: Find logs
    log_files = find_downloaded_logs(args.results_dir)
    if not log_files:
        print("❌ No log files found. Run device testing first.")
        return 1
    
    # Step 3: Analyze logs and generate reports
    reports = analyze_logs_and_generate_reports(log_files, args.output_dir)
    if not reports:
        print("❌ No reports generated. Check log files.")
        return 1
    
    # Step 4: Generate consolidated report
    consolidated_report = generate_consolidated_report(reports, args.output_dir)
    
    # Step 5: Open in browser
    if args.open_browser:
        open_reports_in_browser(consolidated_report)
    
    print("\n🎉 COMPLETE ANALYSIS WORKFLOW FINISHED!")
    print("=" * 80)
    print(f"📊 {len(reports)} reports generated")
    print(f"📂 Output directory: {args.output_dir}")
    print(f"🌐 Main report: {consolidated_report}")
    print("\n💡 Next steps:")
    print("   - Review HTML reports for detailed analysis")
    print("   - Use CSV files for tracking and automation")
    print("   - Fix high-priority memory leaks first")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 