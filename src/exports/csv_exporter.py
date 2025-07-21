"""
CSV Export functionality for Memory Leak Analyzer
Exports leak data in CSV format for spreadsheet analysis
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..models.leak_data import LeakDatabase, MemoryLeak

class CSVExporter:
    """Export memory leak data to CSV format"""
    
    def export_leaks(self, leak_db: LeakDatabase, output_path: Path, include_stack_trace: bool = True):
        """Export all leaks to CSV format"""
        leaks = leak_db.get_all_leaks()
        
        fieldnames = [
            'id', 'leak_type', 'severity', 'size_bytes', 'count', 
            'primary_location', 'message', 'source_file', 'timestamp'
        ]
        
        if include_stack_trace:
            fieldnames.extend(['stack_trace_depth', 'full_stack_trace'])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, leak in enumerate(leaks):
                row = {
                    'id': i + 1,
                    'leak_type': leak.leak_type.value,
                    'severity': leak.get_severity(),
                    'size_bytes': leak.size,
                    'count': leak.count,
                    'primary_location': leak.primary_location,
                    'message': leak.message,
                    'source_file': leak.source_file or '',
                    'timestamp': leak.timestamp.isoformat() if leak.timestamp else ''
                }
                
                if include_stack_trace:
                    row['stack_trace_depth'] = len(leak.stack_trace)
                    row['full_stack_trace'] = ' | '.join(str(frame) for frame in leak.stack_trace)
                
                writer.writerow(row)
    
    def export_statistics(self, leak_db: LeakDatabase, output_path: Path):
        """Export statistics summary to CSV"""
        stats = leak_db.get_statistics()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Memory Leak Analysis Statistics'])
            writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            # Overall stats
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Leaks', stats['total_leaks']])
            writer.writerow(['Total Bytes', stats['total_bytes']])
            writer.writerow([])
            
            # By severity
            writer.writerow(['Severity Breakdown'])
            writer.writerow(['Severity', 'Count'])
            for severity, count in stats['by_severity'].items():
                writer.writerow([severity, count])
            writer.writerow([])
            
            # By type
            writer.writerow(['Type Breakdown'])
            writer.writerow(['Type', 'Count', 'Bytes'])
            for leak_type, info in stats['by_type'].items():
                writer.writerow([leak_type.replace('_', ' ').title(), info['count'], info['bytes']])
            writer.writerow([])
            
            # Top locations
            if stats['top_locations']:
                writer.writerow(['Top Problem Locations'])
                writer.writerow(['Location', 'Count'])
                for location, count in stats['top_locations']:
                    writer.writerow([location, count])
    
    def export_trend_data(self, trend_points: List, output_path: Path):
        """Export trend analysis data to CSV"""
        if not trend_points:
            return
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'version', 'total_leaks', 'total_bytes', 
                         'high_severity', 'medium_severity', 'low_severity', 'notes']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for point in trend_points:
                writer.writerow({
                    'timestamp': point.timestamp.isoformat(),
                    'version': point.version,
                    'total_leaks': point.total_leaks,
                    'total_bytes': point.total_bytes,
                    'high_severity': point.by_severity.get('HIGH', 0),
                    'medium_severity': point.by_severity.get('MEDIUM', 0),
                    'low_severity': point.by_severity.get('LOW', 0),
                    'notes': point.notes
                })
    
    def export_impact_analysis(self, scored_leaks: List, output_path: Path):
        """Export impact analysis results to CSV"""
        fieldnames = [
            'rank', 'impact_category', 'total_score', 'leak_type', 'severity',
            'size_bytes', 'location', 'severity_score', 'size_score', 
            'frequency_score', 'location_score', 'type_score', 'reasoning'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for rank, (leak, impact) in enumerate(scored_leaks, 1):
                writer.writerow({
                    'rank': rank,
                    'impact_category': impact.category.value,
                    'total_score': round(impact.total_score, 3),
                    'leak_type': leak.leak_type.value,
                    'severity': leak.get_severity(),
                    'size_bytes': leak.size,
                    'location': leak.primary_location,
                    'severity_score': round(impact.severity_score, 3),
                    'size_score': round(impact.size_score, 3),
                    'frequency_score': round(impact.frequency_score, 3),
                    'location_score': round(impact.location_score, 3),
                    'type_score': round(impact.type_score, 3),
                    'reasoning': '; '.join(impact.reasoning)
                }) 