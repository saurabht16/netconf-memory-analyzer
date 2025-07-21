"""
CI/CD Integration for Memory Leak Analyzer
Provides tools for integrating memory leak analysis into CI/CD pipelines
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..models.leak_data import LeakDatabase
from ..analysis.trend_analyzer import TrendAnalyzer
from ..analysis.impact_analyzer import ImpactAnalyzer, ImpactCategory

@dataclass
class CIConfig:
    """Configuration for CI/CD integration"""
    fail_on_new_leaks: bool = True
    fail_on_regression: bool = True
    max_allowed_leaks: int = 0
    max_allowed_bytes: int = 0
    critical_threshold: int = 0
    high_threshold: int = 5
    regression_threshold: float = 0.2  # 20% increase
    output_format: str = "json"  # json, junit, github
    
class CIIntegration:
    """Handles CI/CD integration features"""
    
    def __init__(self, config: CIConfig = None):
        self.config = config or CIConfig()
        self.trend_analyzer = TrendAnalyzer()
        self.impact_analyzer = ImpactAnalyzer()
    
    def analyze_for_ci(self, leak_db: LeakDatabase, version: str = "", build_id: str = "") -> Dict[str, Any]:
        """Perform analysis suitable for CI/CD environments"""
        
        # Basic statistics
        stats = leak_db.get_statistics()
        
        # Impact analysis
        impact_analysis = self.impact_analyzer.analyze_database_impact(leak_db)
        
        # Trend analysis (if historical data exists)
        trend_comparison = self.trend_analyzer.compare_with_previous(leak_db, version)
        
        # Determine pass/fail status
        status = self._determine_ci_status(stats, impact_analysis, trend_comparison)
        
        # Generate recommendations
        recommendations = self.impact_analyzer.get_recommendations(leak_db)
        
        result = {
            "status": status["result"],
            "version": version,
            "build_id": build_id,
            "timestamp": leak_db.get_all_leaks()[0].timestamp.isoformat() if leak_db.get_all_leaks() else "",
            "summary": {
                "total_leaks": stats['total_leaks'],
                "total_bytes": stats['total_bytes'],
                "by_severity": stats['by_severity'],
                "critical_issues": impact_analysis.get('category_breakdown', {}).get('critical', 0),
                "high_issues": impact_analysis.get('category_breakdown', {}).get('high', 0)
            },
            "checks": status["checks"],
            "recommendations": recommendations,
            "trend": self._format_trend_data(trend_comparison),
            "exit_code": 0 if status["result"] == "pass" else 1
        }
        
        return result
    
    def _determine_ci_status(self, stats: Dict, impact_analysis: Dict, trend_comparison) -> Dict[str, Any]:
        """Determine if CI build should pass or fail"""
        checks = []
        failures = []
        
        # Check total leak count
        total_leaks = stats['total_leaks']
        if total_leaks > self.config.max_allowed_leaks:
            check = {
                "name": "max_leaks",
                "status": "fail",
                "message": f"Too many leaks: {total_leaks} > {self.config.max_allowed_leaks}"
            }
            failures.append("max_leaks")
        else:
            check = {
                "name": "max_leaks", 
                "status": "pass",
                "message": f"Leak count OK: {total_leaks} <= {self.config.max_allowed_leaks}"
            }
        checks.append(check)
        
        # Check total bytes
        total_bytes = stats['total_bytes']
        if total_bytes > self.config.max_allowed_bytes:
            check = {
                "name": "max_bytes",
                "status": "fail", 
                "message": f"Too much leaked memory: {total_bytes:,} > {self.config.max_allowed_bytes:,} bytes"
            }
            failures.append("max_bytes")
        else:
            check = {
                "name": "max_bytes",
                "status": "pass",
                "message": f"Memory usage OK: {total_bytes:,} <= {self.config.max_allowed_bytes:,} bytes"
            }
        checks.append(check)
        
        # Check critical issues
        if impact_analysis.get('status') == 'success':
            critical_count = impact_analysis.get('category_breakdown', {}).get('critical', 0)
            if critical_count > self.config.critical_threshold:
                check = {
                    "name": "critical_issues",
                    "status": "fail",
                    "message": f"Too many critical issues: {critical_count} > {self.config.critical_threshold}"
                }
                failures.append("critical_issues")
            else:
                check = {
                    "name": "critical_issues",
                    "status": "pass",
                    "message": f"Critical issues OK: {critical_count} <= {self.config.critical_threshold}"
                }
            checks.append(check)
            
            # Check high impact issues
            high_count = impact_analysis.get('category_breakdown', {}).get('high', 0)
            if high_count > self.config.high_threshold:
                check = {
                    "name": "high_issues",
                    "status": "warn",
                    "message": f"Many high-impact issues: {high_count} > {self.config.high_threshold}"
                }
            else:
                check = {
                    "name": "high_issues",
                    "status": "pass",
                    "message": f"High-impact issues OK: {high_count} <= {self.config.high_threshold}"
                }
            checks.append(check)
        
        # Check for regression
        if trend_comparison and self.config.fail_on_regression:
            regression_score = trend_comparison.regression_score
            if regression_score > self.config.regression_threshold:
                check = {
                    "name": "regression",
                    "status": "fail",
                    "message": f"Memory leak regression detected: {regression_score:.1%} increase"
                }
                failures.append("regression")
            else:
                check = {
                    "name": "regression",
                    "status": "pass",
                    "message": f"No significant regression: {regression_score:+.1%} change"
                }
            checks.append(check)
        
        # Determine overall result
        result = "fail" if failures else "pass"
        
        return {
            "result": result,
            "checks": checks,
            "failed_checks": failures
        }
    
    def _format_trend_data(self, trend_comparison) -> Optional[Dict[str, Any]]:
        """Format trend comparison data for CI output"""
        if not trend_comparison:
            return None
        
        return {
            "has_previous_data": True,
            "leak_delta": trend_comparison.leak_delta,
            "bytes_delta": trend_comparison.bytes_delta,
            "regression_score": trend_comparison.regression_score,
            "current_version": trend_comparison.current.version,
            "previous_version": trend_comparison.previous.version
        }
    
    def generate_ci_output(self, analysis_result: Dict[str, Any]) -> str:
        """Generate CI-appropriate output format"""
        
        if self.config.output_format == "json":
            return json.dumps(analysis_result, indent=2)
        
        elif self.config.output_format == "junit":
            return self._generate_junit_xml(analysis_result)
        
        elif self.config.output_format == "github":
            return self._generate_github_output(analysis_result)
        
        else:
            return self._generate_text_output(analysis_result)
    
    def _generate_junit_xml(self, result: Dict[str, Any]) -> str:
        """Generate JUnit XML format for CI systems"""
        
        total_tests = len(result['checks'])
        failures = len([c for c in result['checks'] if c['status'] == 'fail'])
        
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuite name="MemoryLeakAnalysis" tests="{total_tests}" failures="{failures}">',
        ]
        
        for check in result['checks']:
            test_name = check['name']
            xml.append(f'  <testcase name="{test_name}" classname="MemoryLeakCheck">')
            
            if check['status'] == 'fail':
                xml.append(f'    <failure message="{check["message"]}">')
                xml.append(f'      {check["message"]}')
                xml.append('    </failure>')
            
            xml.append('  </testcase>')
        
        xml.append('</testsuite>')
        return '\n'.join(xml)
    
    def _generate_github_output(self, result: Dict[str, Any]) -> str:
        """Generate GitHub Actions output format"""
        
        output = []
        
        # Set GitHub outputs
        output.append(f"::set-output name=status::{result['status']}")
        output.append(f"::set-output name=total_leaks::{result['summary']['total_leaks']}")
        output.append(f"::set-output name=total_bytes::{result['summary']['total_bytes']}")
        output.append(f"::set-output name=exit_code::{result['exit_code']}")
        
        # Add annotations for failures
        for check in result['checks']:
            if check['status'] == 'fail':
                output.append(f"::error title=Memory Leak Check Failed::{check['message']}")
            elif check['status'] == 'warn':
                output.append(f"::warning title=Memory Leak Warning::{check['message']}")
        
        # Summary comment
        summary = f"Memory Leak Analysis: {result['status'].upper()}"
        summary += f" | {result['summary']['total_leaks']} leaks | {result['summary']['total_bytes']:,} bytes"
        output.append(f"::notice title=Analysis Summary::{summary}")
        
        return '\n'.join(output)
    
    def _generate_text_output(self, result: Dict[str, Any]) -> str:
        """Generate human-readable text output"""
        
        output = ["MEMORY LEAK CI ANALYSIS RESULT"]
        output.append("=" * 40)
        output.append(f"Status: {result['status'].upper()}")
        output.append(f"Version: {result['version']}")
        output.append(f"Build ID: {result['build_id']}")
        output.append("")
        
        output.append("SUMMARY:")
        summary = result['summary']
        output.append(f"  Total Leaks: {summary['total_leaks']}")
        output.append(f"  Total Bytes: {summary['total_bytes']:,}")
        output.append(f"  Critical Issues: {summary['critical_issues']}")
        output.append(f"  High Issues: {summary['high_issues']}")
        output.append("")
        
        output.append("CHECK RESULTS:")
        for check in result['checks']:
            status_icon = "✅" if check['status'] == 'pass' else "❌" if check['status'] == 'fail' else "⚠️"
            output.append(f"  {status_icon} {check['name']}: {check['message']}")
        
        if result['recommendations']:
            output.append("")
            output.append("RECOMMENDATIONS:")
            for rec in result['recommendations']:
                output.append(f"  • {rec}")
        
        return '\n'.join(output)
    
    def create_baseline(self, leak_db: LeakDatabase, version: str, notes: str = "Baseline") -> bool:
        """Create a baseline for future comparisons"""
        try:
            self.trend_analyzer.record_analysis(leak_db, version, notes)
            return True
        except Exception as e:
            print(f"Failed to create baseline: {e}")
            return False
    
    def get_exit_code(self, analysis_result: Dict[str, Any]) -> int:
        """Get appropriate exit code for CI"""
        return analysis_result.get('exit_code', 0) 