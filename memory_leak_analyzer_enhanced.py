#!/usr/bin/env python3
"""
Enhanced Memory Leak Analyzer
A comprehensive tool to parse Valgrind XML files and ASan logs with advanced analysis capabilities.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from src.gui.main_window import MemoryLeakGUI
from src.parsers.valgrind_parser import ValgrindParser
from src.parsers.asan_parser import AsanParser
from src.reports.html_generator import HTMLGenerator
from src.models.leak_data import LeakDatabase

# Import advanced features with error handling
try:
    from src.config.config_manager import ConfigManager
except ImportError:
    ConfigManager = None

try:
    from src.analysis.trend_analyzer import TrendAnalyzer
except ImportError:
    TrendAnalyzer = None

try:
    from src.analysis.impact_analyzer import ImpactAnalyzer
except ImportError:
    ImpactAnalyzer = None

try:
    from src.integrations.ci_integration import CIIntegration, CIConfig
except ImportError:
    CIIntegration = None
    CIConfig = None

try:
    from src.exports.csv_exporter import CSVExporter
except ImportError:
    CSVExporter = None


def main():
    parser = argparse.ArgumentParser(description='Enhanced Memory Leak Analyzer - Comprehensive analysis tool')
    
    # Load configuration (optional)
    config_manager = None
    if ConfigManager:
        try:
            config_manager = ConfigManager()
        except Exception:
            config_manager = None
    
    # Basic options
    parser.add_argument('--input', '-i', type=str, help='Input file (Valgrind XML or ASan log)')
    parser.add_argument('--output', '-o', type=str, help='Output HTML file')
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--type', choices=['valgrind', 'asan', 'auto'], default='auto',
                       help='File type (auto-detect by default)')
    
    # Filtering options
    parser.add_argument('--filter-file', type=str, help='Filter by file name pattern')
    parser.add_argument('--filter-dir', type=str, help='Filter by directory pattern')
    parser.add_argument('--filter-function', type=str, help='Filter by function name pattern')
    parser.add_argument('--filter-severity', choices=['HIGH', 'MEDIUM', 'LOW'], 
                       action='append', help='Filter by severity level(s)')
    parser.add_argument('--min-size', type=int, help='Minimum leak size in bytes')
    parser.add_argument('--max-size', type=int, help='Maximum leak size in bytes')
    parser.add_argument('--search', type=str, help='Search term in any field')
    
    # Cleanup options
    parser.add_argument('--cleanup', action='store_true', help='Enable leak cleanup to remove unwanted entries')
    parser.add_argument('--keep-system-libs', action='store_true', help='Keep system library leaks (default: remove)')
    parser.add_argument('--keep-third-party', action='store_true', help='Keep third-party library leaks (default: remove)')
    parser.add_argument('--keep-reachable', action='store_true', help='Keep still-reachable memory (default: remove if cleanup enabled)')
    parser.add_argument('--min-leak-size', type=int, default=8, help='Minimum leak size to include (default: 8 bytes)')
    parser.add_argument('--exclude-pattern', action='append', help='Additional patterns to exclude (can be used multiple times)')
    parser.add_argument('--group-similar', action='store_true', help='Group similar leaks together in output')
    
    # Advanced analysis options
    parser.add_argument('--impact-analysis', action='store_true', help='Perform impact analysis and prioritization')
    parser.add_argument('--trend-analysis', action='store_true', help='Compare with historical data and show trends')
    parser.add_argument('--version', type=str, help='Version/build identifier for trend tracking')
    parser.add_argument('--ci-mode', action='store_true', help='Enable CI/CD integration mode')
    parser.add_argument('--export-csv', type=str, help='Export results to CSV file')
    parser.add_argument('--export-trends-csv', type=str, help='Export trend data to CSV file')
    parser.add_argument('--config-preset', type=str, help='Apply configuration preset (aggressive_cleanup, conservative, development)')
    parser.add_argument('--baseline', action='store_true', help='Create baseline for trend analysis')

    args = parser.parse_args()
    
    try:
        # Apply configuration preset if specified
        if args.config_preset:
            if config_manager and not config_manager.apply_preset(args.config_preset):
                print(f"Warning: Unknown preset '{args.config_preset}'")
                if config_manager:
                    available_presets = list(config_manager.get_presets().keys())
                    print(f"Available presets: {', '.join(available_presets)}")
            elif not config_manager:
                print("Warning: Configuration management not available")
        
        if args.gui:
            # Launch GUI
            app = MemoryLeakGUI()
            app.run()
        else:
            # Command line mode
            if not args.input and not args.export_trends_csv:
                print("Error: --input is required for command line mode (unless exporting trends)")
                return
            
            leak_db = LeakDatabase()
            
            if args.input:
                # Determine file type
                input_path = Path(args.input)
                if not input_path.exists():
                    print(f"Error: Input file '{args.input}' not found")
                    return
                
                if args.type == 'auto':
                    # Auto-detect file type
                    if input_path.suffix.lower() == '.xml':
                        file_type = 'valgrind'
                    else:
                        file_type = 'asan'
                else:
                    file_type = args.type
                
                # Parse file
                print(f"Processing {file_type} file: {args.input}")
                
                if file_type == 'valgrind':
                    parser_obj = ValgrindParser()
                    leaks = parser_obj.parse_file(input_path)
                else:  # asan
                    parser_obj = AsanParser()
                    leaks = parser_obj.parse_file(input_path)
                
                leak_db.add_leaks(leaks)
                
                # Apply cleanup if requested
                if args.cleanup:
                    cleaned_leaks = leak_db.cleanup_leaks(
                        remove_system_libs=not args.keep_system_libs,
                        remove_third_party=not args.keep_third_party,
                        min_leak_size=args.min_leak_size,
                        remove_reachable=not args.keep_reachable,
                        custom_exclude_patterns=args.exclude_pattern
                    )
                    
                    cleanup_stats = leak_db.get_cleanup_stats(cleaned_leaks)
                    print(f"Cleanup: Removed {cleanup_stats['removed_count']} irrelevant leaks "
                          f"({cleanup_stats['removal_percentage']:.1f}%), "
                          f"{cleanup_stats['cleaned_count']} leaks remaining")
                    
                    # Replace original leaks with cleaned ones
                    leak_db.clear()
                    leak_db.add_leaks(cleaned_leaks)
                
                # Create baseline if requested
                if args.baseline:
                    if TrendAnalyzer:
                        trend_analyzer = TrendAnalyzer()
                        version = args.version or "baseline"
                        trend_analyzer.record_analysis(leak_db, version, "Baseline analysis")
                        print(f"Created baseline for version '{version}'")
                        return
                    else:
                        print("Warning: Trend analysis not available")
                
                # Apply filters if specified
                if any([args.filter_file, args.filter_dir, args.filter_function, 
                       args.filter_severity, args.min_size, args.max_size, args.search]):
                    
                    filtered_leaks = leak_db.filter_leaks(
                        file_pattern=args.filter_file,
                        dir_pattern=args.filter_dir,
                        function_pattern=args.filter_function,
                        severities=args.filter_severity,
                        min_size=args.min_size,
                        max_size=args.max_size
                    )
                    
                    if args.search:
                        temp_db = LeakDatabase()
                        temp_db.add_leaks(filtered_leaks)
                        filtered_leaks = temp_db.search_leaks(args.search)
                    
                    print(f"Applied filters: {len(filtered_leaks)} of {len(leak_db.get_all_leaks())} leaks match criteria")
                    
                    # Replace with filtered leaks
                    leak_db.clear()
                    leak_db.add_leaks(filtered_leaks)
            
            # Perform advanced analysis if requested
            if args.impact_analysis:
                if ImpactAnalyzer:
                    impact_analyzer = ImpactAnalyzer()
                    print("\n" + impact_analyzer.generate_priority_report(leak_db))
                    
                    recommendations = impact_analyzer.get_recommendations(leak_db)
                    if recommendations:
                        print("\nRECOMMENDATIONS:")
                        for rec in recommendations:
                            print(f"  {rec}")
                else:
                    print("Warning: Impact analysis not available")
            
            if args.trend_analysis:
                if TrendAnalyzer:
                    trend_analyzer = TrendAnalyzer()
                    if args.version:
                        comparison = trend_analyzer.compare_with_previous(leak_db, args.version)
                        if comparison:
                            print(f"\nTREND ANALYSIS:")
                            print(f"  Previous: {comparison.previous.total_leaks} leaks ({comparison.previous.total_bytes:,} bytes)")
                            print(f"  Current:  {comparison.current.total_leaks} leaks ({comparison.current.total_bytes:,} bytes)")
                            print(f"  Change:   {comparison.leak_delta:+d} leaks ({comparison.bytes_delta:+,} bytes)")
                            print(f"  Regression Score: {comparison.regression_score:+.1%}")
                        else:
                            print("\nNo previous trend data available for comparison")
                    
                    print("\n" + trend_analyzer.generate_trend_report())
                else:
                    print("Warning: Trend analysis not available")
            
            # CI/CD integration mode
            if args.ci_mode:
                if CIIntegration:
                    ci_integration = CIIntegration()
                    result = ci_integration.analyze_for_ci(leak_db, args.version or "", "")
                    print(ci_integration.generate_ci_output(result))
                    sys.exit(result['exit_code'])
                else:
                    print("Warning: CI/CD integration not available")
            
            # Export options
            if args.export_csv:
                if CSVExporter:
                    csv_exporter = CSVExporter()
                    csv_exporter.export_leaks(leak_db, Path(args.export_csv))
                    print(f"Exported leaks to CSV: {args.export_csv}")
                else:
                    print("Warning: CSV export not available")
            
            if args.export_trends_csv:
                if TrendAnalyzer and CSVExporter:
                    trend_analyzer = TrendAnalyzer()
                    history = trend_analyzer.get_trend_history(days=90)
                    if history:
                        csv_exporter = CSVExporter()
                        csv_exporter.export_trend_data(history, Path(args.export_trends_csv))
                        print(f"Exported trend data to CSV: {args.export_trends_csv}")
                    else:
                        print("No trend data available for export")
                else:
                    print("Warning: Trend/CSV export not available")
            
            if args.output:
                # Generate HTML report
                html_generator = HTMLGenerator()
                html_generator.generate_report(leak_db, Path(args.output))
                print(f"HTML report generated: {args.output}")
            else:
                # Print summary to console
                current_leaks = leak_db.get_all_leaks()
                print(f"Total leaks found: {len(current_leaks)}")
                
                if args.group_similar and current_leaks:
                    # Group and display similar leaks
                    groups = leak_db.group_similar_leaks(current_leaks)
                    print(f"Grouped into {len(groups)} patterns:")
                    
                    for signature, group_leaks in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
                        total_size = sum(leak.size for leak in group_leaks)
                        print(f"  {len(group_leaks)}x {signature}: {total_size:,} bytes total")
                        if len(group_leaks) <= 3:  # Show individual leaks for small groups
                            for leak in group_leaks:
                                print(f"    - {leak.leak_type.value}: {leak.size} bytes")
                else:
                    # Display individual leaks
                    for leak in current_leaks:
                        print(f"  {leak.leak_type.value}: {leak.size} bytes at {leak.location}")
                     
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 