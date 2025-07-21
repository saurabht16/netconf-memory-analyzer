#!/usr/bin/env python3
"""
Advanced Features Demo for Memory Leak Analyzer
Demonstrates configuration management, trend analysis, impact scoring, 
CI/CD integration, and export capabilities
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description, capture_output=False):
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"Command: {cmd}")
    print('='*70)
    
    if capture_output:
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.stdout, result.stderr
    else:
        subprocess.run(cmd.split())
        return None, None

def demonstrate_basic_functionality():
    print("📊 BASIC FUNCTIONALITY DEMONSTRATION")
    print("=" * 80)
    
    # Basic analysis
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml",
        "1. Basic analysis (showing all noise)"
    )
    
    # With cleanup
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup",
        "2. Analysis with cleanup (noise removed)"
    )

def demonstrate_configuration():
    print("\n\n⚙️  CONFIGURATION MANAGEMENT DEMONSTRATION")
    print("=" * 80)
    
    # Conservative preset
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --config-preset conservative",
        "3. Using 'conservative' configuration preset"
    )
    
    # Aggressive cleanup preset
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --config-preset aggressive_cleanup",
        "4. Using 'aggressive_cleanup' configuration preset"
    )
    
    # Development preset
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --config-preset development",
        "5. Using 'development' configuration preset"
    )

def demonstrate_trend_analysis():
    print("\n\n📈 TREND ANALYSIS DEMONSTRATION")
    print("=" * 80)
    
    # Create baseline
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --baseline --version v1.0.0",
        "6. Creating baseline for trend analysis (v1.0.0)"
    )
    
    time.sleep(1)  # Small delay to ensure different timestamps
    
    # Simulate version 2 with more leaks
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --trend-analysis --version v1.1.0",
        "7. Analyzing v1.1.0 with trend comparison"
    )
    
    time.sleep(1)
    
    # Simulate version 3 with cleanup
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup --trend-analysis --version v1.2.0",
        "8. Analyzing v1.2.0 with cleanup and trend comparison"
    )

def demonstrate_impact_analysis():
    print("\n\n🎯 IMPACT ANALYSIS DEMONSTRATION")
    print("=" * 80)
    
    # Impact analysis without cleanup
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --impact-analysis",
        "9. Impact analysis (showing prioritization)"
    )
    
    # Impact analysis with cleanup
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup --impact-analysis",
        "10. Impact analysis with cleanup (focused results)"
    )

def demonstrate_ci_integration():
    print("\n\n🔄 CI/CD INTEGRATION DEMONSTRATION")
    print("=" * 80)
    
    # CI mode with passing criteria
    print("\n--- CI Analysis (should PASS) ---")
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_valgrind.xml --ci-mode --version build-123",
        "11. CI/CD mode with clean file (should pass)"
    )
    
    # CI mode with failing criteria
    print("\n--- CI Analysis (may FAIL due to leaks) ---")
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --ci-mode --version build-124",
        "12. CI/CD mode with noisy file (may fail)"
    )

def demonstrate_export_features():
    print("\n\n📤 EXPORT FEATURES DEMONSTRATION")
    print("=" * 80)
    
    # CSV export
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup --export-csv leaks_export.csv",
        "13. Export cleaned leaks to CSV"
    )
    
    # Trend data export
    run_command(
        "python memory_leak_analyzer.py --export-trends-csv trends_export.csv",
        "14. Export trend history to CSV"
    )
    
    # Combined analysis with HTML export
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup --impact-analysis --output advanced_report.html",
        "15. Generate advanced HTML report with all features"
    )

def demonstrate_advanced_combinations():
    print("\n\n🎭 ADVANCED FEATURE COMBINATIONS")
    print("=" * 80)
    
    # Everything together
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup --impact-analysis --trend-analysis --group-similar --version v2.0.0 --export-csv complete_analysis.csv",
        "16. Complete analysis: cleanup + impact + trends + grouping + CSV export"
    )
    
    # Complex filtering with advanced features
    run_command(
        "python memory_leak_analyzer.py --input sample_data/sample_noisy_valgrind.xml --cleanup --filter-severity HIGH --impact-analysis --min-leak-size 100 --group-similar",
        "17. Complex filtering: HIGH severity + large leaks + impact analysis"
    )

def show_generated_files():
    print("\n\n📁 GENERATED FILES")
    print("=" * 80)
    
    generated_files = [
        "leaks_export.csv",
        "trends_export.csv", 
        "advanced_report.html",
        "complete_analysis.csv"
    ]
    
    for filename in generated_files:
        if Path(filename).exists():
            size = Path(filename).stat().st_size
            print(f"✅ {filename} ({size:,} bytes)")
        else:
            print(f"❌ {filename} (not found)")
    
    # Show config directory
    config_dir = Path.home() / ".memory_leak_analyzer"
    if config_dir.exists():
        print(f"\n📂 Configuration directory: {config_dir}")
        for file in config_dir.iterdir():
            if file.is_file():
                print(f"   {file.name}")

def demonstrate_gui_features():
    print("\n\n🖥️  GUI FEATURES")
    print("=" * 80)
    print("The GUI now includes:")
    print("  ✅ Real-time search and filtering")
    print("  ✅ Cleanup options with checkboxes")
    print("  ✅ Export filtered results to HTML")
    print("  ✅ Advanced filtering by file, function, severity")
    print("  ✅ Statistical summaries and charts")
    print("\nTo test GUI features, run:")
    print("  python memory_leak_analyzer.py --gui")

def main():
    print("🧠 MEMORY LEAK ANALYZER - ADVANCED FEATURES DEMONSTRATION")
    print("=" * 80)
    print("This demo showcases the robust and dynamic features of the analyzer:")
    print()
    print("🔧 Configuration Management - User presets and customizable settings")
    print("📈 Trend Analysis - Track memory leaks over time and builds")
    print("🎯 Impact Analysis - Smart prioritization and scoring")
    print("🔄 CI/CD Integration - Automated quality gates")
    print("📤 Multiple Export Formats - CSV, HTML, JSON")
    print("🧹 Advanced Cleanup - Intelligent noise reduction")
    print("🔍 Smart Filtering - Multi-criteria search and filter")
    print("🖥️  Enhanced GUI - Real-time filtering and export")
    
    print("\n" + "=" * 80)
    print("Starting demonstration...")
    
    # Run all demonstrations
    demonstrate_basic_functionality()
    demonstrate_configuration()
    demonstrate_trend_analysis()
    demonstrate_impact_analysis()
    demonstrate_ci_integration()
    demonstrate_export_features()
    demonstrate_advanced_combinations()
    demonstrate_gui_features()
    show_generated_files()
    
    print("\n" + "=" * 80)
    print("🎉 ADVANCED FEATURES DEMONSTRATION COMPLETED!")
    print("=" * 80)
    print("\n✨ NEW ROBUST & DYNAMIC FEATURES SUMMARY:")
    print()
    print("📋 CONFIGURATION & PRESETS:")
    print("   • User-configurable settings with YAML support")
    print("   • Built-in presets: conservative, aggressive_cleanup, development")
    print("   • Custom exclude patterns and analysis preferences")
    print()
    print("📊 ADVANCED ANALYSIS:")
    print("   • Trend analysis with SQLite-based historical tracking")
    print("   • Smart impact scoring with 5-factor algorithm")
    print("   • Regression detection and performance tracking")
    print("   • Leak pattern grouping and frequency analysis")
    print()
    print("🔗 INTEGRATIONS:")
    print("   • CI/CD pipeline integration with pass/fail logic")
    print("   • Multiple output formats: JSON, JUnit XML, GitHub Actions")
    print("   • Configurable quality gates and thresholds")
    print("   • Exit codes for automated workflows")
    print()
    print("📤 EXPORT & REPORTING:")
    print("   • CSV exports for spreadsheet analysis")
    print("   • Enhanced HTML reports with client-side filtering")
    print("   • Trend data exports for external analysis")
    print("   • Statistical summaries and impact breakdowns")
    print()
    print("🧹 INTELLIGENT CLEANUP:")
    print("   • System library noise removal")
    print("   • Third-party library filtering")
    print("   • Configurable size thresholds")
    print("   • Custom exclude patterns")
    print("   • Suppressed error handling")
    print()
    print("🎯 SMART FEATURES:")
    print("   • Multi-criteria impact scoring")
    print("   • Automated leak categorization")
    print("   • Priority-based recommendations")
    print("   • Pattern recognition and grouping")
    print("   • Context-aware location scoring")
    print()
    print("🔧 ROBUSTNESS:")
    print("   • Error handling and graceful degradation")
    print("   • Configurable memory limits and processing")
    print("   • Cross-platform compatibility (Linux, macOS, Windows)")
    print("   • Python 3.7+ support with type annotations")
    print("   • SQLite-based persistence for reliability")
    print()
    print("This analyzer is now a comprehensive, enterprise-ready solution")
    print("for memory leak detection, analysis, and management! 🚀")

if __name__ == "__main__":
    main() 