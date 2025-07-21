"""
Trend Analysis for Memory Leak Analyzer
Tracks changes in memory leaks over time, compares builds/versions
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib

from ..models.leak_data import LeakDatabase, MemoryLeak, LeakType

@dataclass
class TrendPoint:
    """A single point in trend analysis"""
    timestamp: datetime
    version: str
    total_leaks: int
    total_bytes: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    file_hash: str
    notes: str = ""

@dataclass
class TrendComparison:
    """Comparison between two trend points"""
    current: TrendPoint
    previous: TrendPoint
    leak_delta: int
    bytes_delta: int
    new_leaks: List[MemoryLeak]
    fixed_leaks: List[MemoryLeak]
    regression_score: float

class TrendAnalyzer:
    """Analyzes trends in memory leak data over time"""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".memory_leak_analyzer" / "trends.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the trends database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trend_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    version TEXT,
                    total_leaks INTEGER,
                    total_bytes INTEGER,
                    severity_data TEXT,
                    type_data TEXT,
                    file_hash TEXT,
                    notes TEXT,
                    raw_data TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON trend_points(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_version ON trend_points(version)
            """)
    
    def record_analysis(self, leak_db: LeakDatabase, version: str = "", notes: str = "", file_path: Optional[Path] = None) -> TrendPoint:
        """Record a new analysis result for trend tracking"""
        stats = leak_db.get_statistics()
        leaks = leak_db.get_all_leaks()
        
        # Create a hash of the leak data for detecting duplicates
        leak_signatures = []
        for leak in leaks:
            sig = f"{leak.leak_type.value}:{leak.size}:{leak.primary_location}"
            leak_signatures.append(sig)
        
        data_hash = hashlib.md5("\n".join(sorted(leak_signatures)).encode()).hexdigest()
        
        # Calculate file hash if file provided
        file_hash = ""
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
        
        trend_point = TrendPoint(
            timestamp=datetime.now(),
            version=version or datetime.now().strftime("%Y%m%d_%H%M%S"),
            total_leaks=stats['total_leaks'],
            total_bytes=stats['total_bytes'],
            by_severity=stats['by_severity'],
            by_type={k: v['count'] for k, v in stats['by_type'].items()},
            file_hash=file_hash,
            notes=notes
        )
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trend_points 
                (timestamp, version, total_leaks, total_bytes, severity_data, type_data, file_hash, notes, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trend_point.timestamp.isoformat(),
                trend_point.version,
                trend_point.total_leaks,
                trend_point.total_bytes,
                json.dumps(trend_point.by_severity),
                json.dumps(trend_point.by_type),
                trend_point.file_hash,
                trend_point.notes,
                data_hash
            ))
        
        return trend_point
    
    def get_trend_history(self, days: int = 30, version_pattern: str = "") -> List[TrendPoint]:
        """Get trend history for the specified period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, version, total_leaks, total_bytes, severity_data, type_data, file_hash, notes
                FROM trend_points 
                WHERE timestamp >= ?
            """
            params = [cutoff_date.isoformat()]
            
            if version_pattern:
                query += " AND version LIKE ?"
                params.append(f"%{version_pattern}%")
            
            query += " ORDER BY timestamp"
            
            cursor = conn.execute(query, params)
            
            trends = []
            for row in cursor:
                trends.append(TrendPoint(
                    timestamp=datetime.fromisoformat(row[0]),
                    version=row[1],
                    total_leaks=row[2],
                    total_bytes=row[3],
                    by_severity=json.loads(row[4]),
                    by_type=json.loads(row[5]),
                    file_hash=row[6],
                    notes=row[7]
                ))
            
            return trends
    
    def compare_with_previous(self, current_db: LeakDatabase, version: str = "") -> Optional[TrendComparison]:
        """Compare current analysis with the most recent previous analysis"""
        # Record current analysis
        current_point = self.record_analysis(current_db, version)
        
        # Get previous analysis
        history = self.get_trend_history(days=90)  # Look back 90 days
        if len(history) < 2:
            return None
        
        # Find the most recent previous point (excluding current)
        previous_point = history[-2]  # Second to last
        
        # Calculate deltas
        leak_delta = current_point.total_leaks - previous_point.total_leaks
        bytes_delta = current_point.total_bytes - previous_point.total_bytes
        
        # Calculate regression score (higher = worse)
        regression_score = 0.0
        if previous_point.total_leaks > 0:
            leak_regression = leak_delta / previous_point.total_leaks
            bytes_regression = bytes_delta / max(previous_point.total_bytes, 1)
            
            # Weight high severity leaks more heavily
            high_severity_delta = (current_point.by_severity.get('HIGH', 0) - 
                                 previous_point.by_severity.get('HIGH', 0))
            
            regression_score = (leak_regression * 0.4 + 
                              bytes_regression * 0.3 + 
                              high_severity_delta * 0.3)
        
        return TrendComparison(
            current=current_point,
            previous=previous_point,
            leak_delta=leak_delta,
            bytes_delta=bytes_delta,
            new_leaks=[],  # TODO: Implement detailed leak comparison
            fixed_leaks=[],
            regression_score=regression_score
        )
    
    def get_trend_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get a summary of trends over the specified period"""
        history = self.get_trend_history(days)
        
        if not history:
            return {"status": "no_data"}
        
        # Calculate trend metrics
        start_point = history[0]
        end_point = history[-1]
        
        total_change = end_point.total_leaks - start_point.total_leaks
        bytes_change = end_point.total_bytes - start_point.total_bytes
        
        # Find peaks and valleys
        max_leaks = max(point.total_leaks for point in history)
        min_leaks = min(point.total_leaks for point in history)
        
        # Calculate average change per day
        if len(history) > 1:
            days_span = (end_point.timestamp - start_point.timestamp).days or 1
            avg_daily_change = total_change / days_span
        else:
            avg_daily_change = 0
        
        # Determine trend direction
        if total_change > 0:
            trend = "worsening"
        elif total_change < 0:
            trend = "improving"
        else:
            trend = "stable"
        
        return {
            "status": "success",
            "trend_direction": trend,
            "total_change": total_change,
            "bytes_change": bytes_change,
            "avg_daily_change": avg_daily_change,
            "peak_leaks": max_leaks,
            "min_leaks": min_leaks,
            "analysis_count": len(history),
            "time_span_days": days,
            "latest_version": end_point.version,
            "latest_analysis": end_point.timestamp.isoformat()
        }
    
    def generate_trend_report(self, days: int = 30) -> str:
        """Generate a text report of trends"""
        summary = self.get_trend_summary(days)
        history = self.get_trend_history(days)
        
        if summary["status"] != "success":
            return "No trend data available."
        
        report = ["MEMORY LEAK TREND ANALYSIS REPORT"]
        report.append("=" * 50)
        report.append(f"Analysis Period: {days} days")
        report.append(f"Total Analyses: {summary['analysis_count']}")
        report.append(f"Latest Version: {summary['latest_version']}")
        report.append("")
        
        report.append("TREND SUMMARY:")
        report.append(f"  Direction: {summary['trend_direction'].upper()}")
        report.append(f"  Total Change: {summary['total_change']:+d} leaks")
        report.append(f"  Memory Change: {summary['bytes_change']:+,} bytes")
        report.append(f"  Daily Average: {summary['avg_daily_change']:+.1f} leaks/day")
        report.append("")
        
        report.append("EXTREMES:")
        report.append(f"  Peak Leaks: {summary['peak_leaks']:,}")
        report.append(f"  Minimum Leaks: {summary['min_leaks']:,}")
        report.append("")
        
        if len(history) >= 5:
            report.append("RECENT HISTORY:")
            for point in history[-5:]:
                date_str = point.timestamp.strftime("%Y-%m-%d %H:%M")
                report.append(f"  {date_str} | {point.version:15} | {point.total_leaks:4d} leaks | {point.total_bytes:8,} bytes")
        
        return "\n".join(report)
    
    def cleanup_old_data(self, keep_days: int = 365):
        """Remove trend data older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM trend_points WHERE timestamp < ?",
                [cutoff_date.isoformat()]
            )
            
            return cursor.rowcount 