#!/usr/bin/env python3
"""
Memory Leak Analyzer
A tool to parse Valgrind XML files and ASan logs, and display results in GUI or HTML format.
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


def main():
    parser = argparse.ArgumentParser(description='Memory Leak Analyzer')
    parser.add_argument('--input', '-i', type=str, help='Input file (Valgrind XML or ASan log)')
    parser.add_argument('--output', '-o', type=str, help='Output HTML file')
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--type', choices=['valgrind', 'asan', 'auto'], default='auto',
                       help='File type (auto-detect by default)')
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
    
    if args.gui or (not args.input and not args.export_trends_csv):
        # Launch GUI mode
        app = MemoryLeakGUI()
        app.run()
    else:
        # Command line mode
        
        # Handle trend export without input file
        if args.export_trends_csv and not args.input:
            try:
                # Import with error handling
                from src.analysis.trend_analyzer import TrendAnalyzer
                from src.exports.csv_exporter import CSVExporter
                
                trend_analyzer = TrendAnalyzer()
                history = trend_analyzer.get_trend_history(days=90)
                if history:
                    csv_exporter = CSVExporter()
                    csv_exporter.export_trend_data(history, Path(args.export_trends_csv))
                    print(f"Exported {len(history)} trend data points to CSV: {args.export_trends_csv}")
                else:
                    print("No trend data available for export")
                return
            except ImportError:
                print("Error: Trend analysis or CSV export modules not available")
                return
            except Exception as e:
                print(f"Error exporting trend data: {e}")
                return
        
        if not args.input:
            print("Error: --input is required for analysis")
            sys.exit(1)
            
        input_file = Path(args.input)
        if not input_file.exists():
            print(f"Error: Input file '{input_file}' not found")
            sys.exit(1)
            
        # Auto-detect file type if needed
        file_type = args.type
        if file_type == 'auto':
            if input_file.suffix.lower() == '.xml':
                file_type = 'valgrind'
            else:
                file_type = 'asan'
        
        # Parse the file
        leak_db = LeakDatabase()
        
        try:
            if file_type == 'valgrind':
                parser_instance = ValgrindParser()
                leaks = parser_instance.parse_file(input_file)
            else:
                parser_instance = AsanParser()
                leaks = parser_instance.parse_file(input_file)
            
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
                
                if args.search:
                    filtered_leaks = leak_db.search_leaks(args.search)
                else:
                    filtered_leaks = leak_db.filter_leaks(
                        file_pattern=args.filter_file,
                        directory_pattern=args.filter_dir,
                        function_pattern=args.filter_function,
                        severities=args.filter_severity,
                        min_size=args.min_size,
                        max_size=args.max_size
                    )
                
                # Create a new database with filtered results
                filtered_db = LeakDatabase()
                filtered_db.add_leaks(filtered_leaks)
                leak_db = filtered_db
                
                print(f"Applied filters: {len(filtered_leaks)} leaks match criteria")
            
            # Generate output
            if args.output:
                output_file = Path(args.output)
                html_gen = HTMLGenerator()
                html_gen.generate_report(leak_db, output_file)
                print(f"HTML report generated: {output_file}")
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


if __name__ == '__main__':
    main() 