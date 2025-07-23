#!/usr/bin/env python3
"""
Memory Leak Report Comparison Tool
Compare two memory leak analysis reports to identify improvements, regressions, and trends
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.leak_data import LeakDatabase, MemoryLeak
from src.parsers.valgrind_parser import ValgrindParser
from src.parsers.asan_parser import AsanParser
from src.analysis.trend_analyzer import TrendAnalyzer, TrendPoint, TrendComparison
from src.reports.html_generator import HTMLGenerator

class ReportComparator:
    """Compare two memory leak analysis reports"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def compare_reports(self, baseline_file: Path, current_file: Path, 
                       baseline_version: str = "baseline", 
                       current_version: str = "current") -> Dict[str, Any]:
        """Compare two report files and return comparison results"""
        
        # Parse baseline report
        baseline_db = self._parse_report_file(baseline_file)
        if not baseline_db:
            raise ValueError(f"Failed to parse baseline report: {baseline_file}")
        
        # Parse current report  
        current_db = self._parse_report_file(current_file)
        if not current_db:
            raise ValueError(f"Failed to parse current report: {current_file}")
        
        # Perform comparison
        comparison = self._compare_leak_databases(
            baseline_db, current_db, baseline_version, current_version
        )
        
        return comparison
    
    def _parse_report_file(self, file_path: Path) -> Optional[LeakDatabase]:
        """Parse a Valgrind XML or ASan log file"""
        try:
            leak_db = LeakDatabase()
            
            # Determine file type and parse accordingly
            file_content = file_path.read_text()
            
            if file_path.suffix.lower() == '.xml' or '<?xml' in file_content:
                # Valgrind XML file
                parser = ValgrindParser()
                leaks = parser.parse_file(file_path)
            else:
                # ASan log file
                parser = AsanParser()
                leaks = parser.parse_file(file_path)
            
            leak_db.add_leaks(leaks)
            return leak_db
            
        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            return None
    
    def _compare_leak_databases(self, baseline: LeakDatabase, current: LeakDatabase,
                               baseline_version: str, current_version: str) -> Dict[str, Any]:
        """Compare two leak databases and generate detailed comparison"""
        
        # Get statistics for both
        baseline_stats = baseline.get_statistics()
        current_stats = current.get_statistics()
        
        # Calculate deltas
        leak_delta = current_stats['total_leaks'] - baseline_stats['total_leaks']
        bytes_delta = current_stats['total_bytes'] - baseline_stats['total_bytes']
        
        # Find new and fixed leaks
        new_leaks, fixed_leaks = self._find_leak_differences(baseline, current)
        
        # Calculate regression score (0-100, higher is worse)
        regression_score = self._calculate_regression_score(
            leak_delta, bytes_delta, len(new_leaks), len(fixed_leaks)
        )
        
        # Create detailed comparison
        comparison = {
            'baseline': {
                'version': baseline_version,
                'file_path': str(baseline_stats.get('source_file', 'unknown')),
                'total_leaks': baseline_stats['total_leaks'],
                'total_bytes': baseline_stats['total_bytes'],
                'by_severity': baseline_stats['by_severity'],
                'by_type': baseline_stats['by_type']
            },
            'current': {
                'version': current_version,
                'file_path': str(current_stats.get('source_file', 'unknown')),
                'total_leaks': current_stats['total_leaks'],
                'total_bytes': current_stats['total_bytes'],
                'by_severity': current_stats['by_severity'],
                'by_type': current_stats['by_type']
            },
            'comparison': {
                'leak_delta': leak_delta,
                'bytes_delta': bytes_delta,
                'leak_change_percent': self._calculate_percentage_change(
                    baseline_stats['total_leaks'], current_stats['total_leaks']
                ),
                'bytes_change_percent': self._calculate_percentage_change(
                    baseline_stats['total_bytes'], current_stats['total_bytes']
                ),
                'regression_score': regression_score,
                'status': self._determine_status(leak_delta, bytes_delta, regression_score)
            },
            'new_leaks': [self._leak_to_dict(leak) for leak in new_leaks[:10]],  # Top 10
            'fixed_leaks': [self._leak_to_dict(leak) for leak in fixed_leaks[:10]],  # Top 10
            'new_leaks_count': len(new_leaks),
            'fixed_leaks_count': len(fixed_leaks),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return comparison
    
    def _find_leak_differences(self, baseline: LeakDatabase, current: LeakDatabase) -> Tuple[List[MemoryLeak], List[MemoryLeak]]:
        """Find leaks that are new in current vs baseline, and leaks that were fixed"""
        
        # Create fingerprints for leaks (based on stack trace and size)
        def leak_fingerprint(leak):
            # Use stack trace + size for fingerprint
            stack_str = " -> ".join([frame.function for frame in leak.stack_trace if frame.function])
            return f"{leak.size}_{hash(stack_str) % 100000}"
        
        baseline_fingerprints = {leak_fingerprint(leak): leak for leak in baseline.get_all_leaks()}
        current_fingerprints = {leak_fingerprint(leak): leak for leak in current.get_all_leaks()}
        
        # Find new leaks (in current but not in baseline)
        new_leaks = [
            leak for fp, leak in current_fingerprints.items() 
            if fp not in baseline_fingerprints
        ]
        
        # Find fixed leaks (in baseline but not in current)
        fixed_leaks = [
            leak for fp, leak in baseline_fingerprints.items()
            if fp not in current_fingerprints
        ]
        
        # Sort by size (largest first)
        new_leaks.sort(key=lambda x: x.size, reverse=True)
        fixed_leaks.sort(key=lambda x: x.size, reverse=True)
        
        return new_leaks, fixed_leaks
    
    def _calculate_percentage_change(self, old_value: int, new_value: int) -> float:
        """Calculate percentage change from old to new value"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return ((new_value - old_value) / old_value) * 100.0
    
    def _calculate_regression_score(self, leak_delta: int, bytes_delta: int, 
                                  new_leaks: int, fixed_leaks: int) -> float:
        """Calculate regression score (0-100, higher is worse)"""
        
        # Base score from leak count change
        leak_score = max(0, leak_delta * 5)  # 5 points per new leak
        
        # Score from bytes change (normalized)
        bytes_score = max(0, bytes_delta / 1024)  # 1 point per KB
        
        # Penalty for new leaks, bonus for fixed leaks
        balance_score = (new_leaks * 3) - (fixed_leaks * 1)
        
        total_score = leak_score + bytes_score + balance_score
        
        # Cap at 100
        return min(100.0, max(0.0, total_score))
    
    def _determine_status(self, leak_delta: int, bytes_delta: int, regression_score: float) -> str:
        """Determine overall status of the comparison"""
        if regression_score > 50:
            return "MAJOR_REGRESSION"
        elif regression_score > 20:
            return "REGRESSION"
        elif leak_delta <= 0 and bytes_delta <= 0:
            return "IMPROVEMENT"
        elif leak_delta == 0 and bytes_delta == 0:
            return "NO_CHANGE"
        else:
            return "MINOR_REGRESSION"
    
    def _leak_to_dict(self, leak: MemoryLeak) -> Dict[str, Any]:
        """Convert MemoryLeak to dictionary for JSON serialization"""
        return {
            'size': leak.size,
            'leak_type': leak.leak_type.value if hasattr(leak.leak_type, 'value') else str(leak.leak_type),
            'severity': leak.severity,
            'function': leak.stack_trace[0].function if leak.stack_trace else 'unknown',
            'file': leak.stack_trace[0].file if leak.stack_trace else 'unknown',
            'line': leak.stack_trace[0].line if leak.stack_trace else 0,
            'stack_depth': len(leak.stack_trace)
        }
    
    def generate_comparison_report(self, comparison: Dict[str, Any], output_file: Path):
        """Generate HTML comparison report"""
        
        html_content = self._generate_comparison_html(comparison)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Comparison report generated: {output_file}")
    
    def _generate_comparison_html(self, comparison: Dict[str, Any]) -> str:
        """Generate HTML content for comparison report"""
        
        status = comparison['comparison']['status']
        status_color = {
            'IMPROVEMENT': '#28a745',
            'NO_CHANGE': '#6c757d',
            'MINOR_REGRESSION': '#ffc107',
            'REGRESSION': '#fd7e14',
            'MAJOR_REGRESSION': '#dc3545'
        }.get(status, '#6c757d')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Memory Leak Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status {{ padding: 10px 20px; border-radius: 5px; color: white; font-weight: bold; display: inline-block; }}
        .metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
        .metric-box {{ padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: #f8f9fa; }}
        .metric-title {{ font-weight: bold; color: #495057; margin-bottom: 10px; }}
        .delta-positive {{ color: #dc3545; }}
        .delta-negative {{ color: #28a745; }}
        .delta-zero {{ color: #6c757d; }}
        .leak-list {{ margin: 15px 0; }}
        .leak-item {{ padding: 8px; margin: 5px 0; border-left: 4px solid #007bff; background: #f8f9fa; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #e9ecef; font-weight: bold; }}
        .summary {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Memory Leak Comparison Report</h1>
            <div class="status" style="background-color: {status_color};">
                Status: {status.replace('_', ' ')}
            </div>
        </div>
        
        <div class="summary">
            <h2>📊 Summary</h2>
            <p><strong>Baseline:</strong> {comparison['baseline']['version']} ({comparison['baseline']['total_leaks']} leaks, {comparison['baseline']['total_bytes']:,} bytes)</p>
            <p><strong>Current:</strong> {comparison['current']['version']} ({comparison['current']['total_leaks']} leaks, {comparison['current']['total_bytes']:,} bytes)</p>
            <p><strong>Regression Score:</strong> {comparison['comparison']['regression_score']:.1f}/100</p>
        </div>
        
        <div class="metrics">
            <div class="metric-box">
                <div class="metric-title">📈 Leak Count Change</div>
                <div class="{'delta-positive' if comparison['comparison']['leak_delta'] > 0 else 'delta-negative' if comparison['comparison']['leak_delta'] < 0 else 'delta-zero'}">
                    {comparison['comparison']['leak_delta']:+d} leaks 
                    ({comparison['comparison']['leak_change_percent']:+.1f}%)
                </div>
            </div>
            
            <div class="metric-box">
                <div class="metric-title">💾 Memory Change</div>
                <div class="{'delta-positive' if comparison['comparison']['bytes_delta'] > 0 else 'delta-negative' if comparison['comparison']['bytes_delta'] < 0 else 'delta-zero'}">
                    {comparison['comparison']['bytes_delta']:+,} bytes 
                    ({comparison['comparison']['bytes_change_percent']:+.1f}%)
                </div>
            </div>
        </div>
        
        <h2>🆕 New Leaks ({comparison['new_leaks_count']} total)</h2>
        <div class="leak-list">
"""
        
        # Add new leaks
        for leak in comparison['new_leaks'][:10]:
            html += f"""
            <div class="leak-item">
                <strong>{leak['size']:,} bytes</strong> - {leak['function']} 
                <small>({leak['file']}:{leak['line']})</small>
            </div>
"""
        
        html += f"""
        </div>
        
        <h2>✅ Fixed Leaks ({comparison['fixed_leaks_count']} total)</h2>
        <div class="leak-list">
"""
        
        # Add fixed leaks
        for leak in comparison['fixed_leaks'][:10]:
            html += f"""
            <div class="leak-item">
                <strong>{leak['size']:,} bytes</strong> - {leak['function']} 
                <small>({leak['file']}:{leak['line']})</small>
            </div>
"""
        
        html += f"""
        </div>
        
        <h2>📋 Detailed Comparison</h2>
        <table>
            <tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Change</th></tr>
            <tr>
                <td>Total Leaks</td>
                <td>{comparison['baseline']['total_leaks']}</td>
                <td>{comparison['current']['total_leaks']}</td>
                <td class="{'delta-positive' if comparison['comparison']['leak_delta'] > 0 else 'delta-negative' if comparison['comparison']['leak_delta'] < 0 else 'delta-zero'}">{comparison['comparison']['leak_delta']:+d}</td>
            </tr>
            <tr>
                <td>Total Bytes</td>
                <td>{comparison['baseline']['total_bytes']:,}</td>
                <td>{comparison['current']['total_bytes']:,}</td>
                <td class="{'delta-positive' if comparison['comparison']['bytes_delta'] > 0 else 'delta-negative' if comparison['comparison']['bytes_delta'] < 0 else 'delta-zero'}">{comparison['comparison']['bytes_delta']:+,}</td>
            </tr>
        </table>
        
        <div style="margin-top: 30px; text-align: center; color: #6c757d; font-size: 12px;">
            Generated on {comparison['analysis_timestamp']} by NETCONF Memory Leak Analyzer
        </div>
    </div>
</body>
</html>
"""
        
        return html

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Compare Memory Leak Analysis Reports')
    
    parser.add_argument('--baseline', type=Path, required=True,
                       help='Baseline report file (Valgrind XML or ASan log)')
    parser.add_argument('--current', type=Path, required=True,
                       help='Current report file (Valgrind XML or ASan log)')
    parser.add_argument('--baseline-version', type=str, default='baseline',
                       help='Version identifier for baseline')
    parser.add_argument('--current-version', type=str, default='current',
                       help='Version identifier for current')
    parser.add_argument('--output', type=Path, default='comparison_report.html',
                       help='Output HTML report file')
    parser.add_argument('--json-output', type=Path,
                       help='Also save comparison data as JSON')
    parser.add_argument('--threshold', type=float, default=20.0,
                       help='Regression score threshold for failure (default: 20.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validate input files
        if not args.baseline.exists():
            logger.error(f"Baseline file not found: {args.baseline}")
            return 1
        
        if not args.current.exists():
            logger.error(f"Current file not found: {args.current}")
            return 1
        
        # Perform comparison
        comparator = ReportComparator()
        logger.info(f"Comparing {args.baseline} vs {args.current}")
        
        comparison = comparator.compare_reports(
            args.baseline, args.current,
            args.baseline_version, args.current_version
        )
        
        # Generate HTML report
        comparator.generate_comparison_report(comparison, args.output)
        logger.info(f"HTML report generated: {args.output}")
        
        # Save JSON output if requested
        if args.json_output:
            with open(args.json_output, 'w') as f:
                json.dump(comparison, f, indent=2)
            logger.info(f"JSON data saved: {args.json_output}")
        
        # Print summary
        comp = comparison['comparison']
        print(f"\n🔍 COMPARISON SUMMARY")
        print(f"{'='*50}")
        print(f"Status: {comp['status']}")
        print(f"Leak Delta: {comp['leak_delta']:+d} ({comp['leak_change_percent']:+.1f}%)")
        print(f"Bytes Delta: {comp['bytes_delta']:+,} ({comp['bytes_change_percent']:+.1f}%)")
        print(f"Regression Score: {comp['regression_score']:.1f}/100")
        print(f"New Leaks: {comparison['new_leaks_count']}")
        print(f"Fixed Leaks: {comparison['fixed_leaks_count']}")
        
        # Exit with appropriate code
        if comp['regression_score'] > args.threshold:
            logger.warning(f"Regression score {comp['regression_score']:.1f} exceeds threshold {args.threshold}")
            return 1
        else:
            logger.info("Comparison completed successfully")
            return 0
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 