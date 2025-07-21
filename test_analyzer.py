#!/usr/bin/env python3
"""
Test script for Memory Leak Analyzer
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.append('src')

from src.parsers.valgrind_parser import ValgrindParser
from src.parsers.asan_parser import AsanParser
from src.models.leak_data import LeakDatabase
from src.reports.html_generator import HTMLGenerator

def test_valgrind_parser():
    """Test Valgrind parser"""
    print("Testing Valgrind parser...")
    parser = ValgrindParser()
    
    # Test validation
    xml_file = Path("sample_data/sample_valgrind.xml")
    if xml_file.exists():
        is_valid = parser.validate_file(xml_file)
        print(f"  Validation: {'PASS' if is_valid else 'FAIL'}")
        
        # Test parsing
        try:
            leaks = parser.parse_file(xml_file)
            print(f"  Parsed {len(leaks)} leaks: PASS")
            for leak in leaks:
                print(f"    - {leak.leak_type.value}: {leak.size} bytes")
        except Exception as e:
            print(f"  Parsing: FAIL - {e}")
    else:
        print("  Sample file not found: SKIP")

def test_asan_parser():
    """Test ASan parser"""
    print("\nTesting ASan parser...")
    parser = AsanParser()
    
    # Test validation
    log_file = Path("sample_data/sample_asan.log")
    if log_file.exists():
        is_valid = parser.validate_file(log_file)
        print(f"  Validation: {'PASS' if is_valid else 'FAIL'}")
        
        # Test parsing
        try:
            leaks = parser.parse_file(log_file)
            print(f"  Parsed {len(leaks)} errors: PASS")
            for leak in leaks:
                print(f"    - {leak.leak_type.value}: {leak.size} bytes")
        except Exception as e:
            print(f"  Parsing: FAIL - {e}")
    else:
        print("  Sample file not found: SKIP")

def test_html_generator():
    """Test HTML report generator"""
    print("\nTesting HTML generator...")
    
    # Create a sample leak database
    db = LeakDatabase()
    parser = ValgrindParser()
    
    xml_file = Path("sample_data/sample_valgrind.xml")
    if xml_file.exists():
        leaks = parser.parse_file(xml_file)
        db.add_leaks(leaks)
        
        # Generate HTML report
        generator = HTMLGenerator()
        output_file = Path("test_output.html")
        
        try:
            generator.generate_report(db, output_file)
            if output_file.exists():
                print("  HTML generation: PASS")
                print(f"  Report saved: {output_file}")
            else:
                print("  HTML generation: FAIL - File not created")
        except Exception as e:
            print(f"  HTML generation: FAIL - {e}")
    else:
        print("  Sample file not found: SKIP")

def test_statistics():
    """Test statistics calculation"""
    print("\nTesting statistics...")
    
    db = LeakDatabase()
    parser = ValgrindParser()
    
    xml_file = Path("sample_data/sample_valgrind.xml")
    if xml_file.exists():
        leaks = parser.parse_file(xml_file)
        db.add_leaks(leaks)
        
        stats = db.get_statistics()
        print(f"  Total leaks: {stats['total_leaks']}")
        print(f"  Total bytes: {stats['total_bytes']}")
        print(f"  By severity: {stats['by_severity']}")
        print("  Statistics: PASS")
    else:
        print("  Sample file not found: SKIP")

def main():
    """Run all tests"""
    print("Memory Leak Analyzer - Test Suite")
    print("=" * 40)
    
    test_valgrind_parser()
    test_asan_parser()
    test_html_generator()
    test_statistics()
    
    print("\n" + "=" * 40)
    print("Test suite completed!")

if __name__ == "__main__":
    main() 