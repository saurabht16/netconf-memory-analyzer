"""
Impact Analysis for Memory Leak Analyzer
Scores and prioritizes memory leaks based on various factors
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re

from ..models.leak_data import MemoryLeak, LeakType, LeakDatabase

class ImpactCategory(Enum):
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"

@dataclass
class ImpactScore:
    """Impact score for a memory leak"""
    total_score: float
    category: ImpactCategory
    severity_score: float
    size_score: float
    frequency_score: float
    location_score: float
    type_score: float
    reasoning: List[str]

class ImpactAnalyzer:
    """Analyzes and scores memory leaks by impact"""
    
    def __init__(self):
        # Critical function patterns that indicate high impact
        self.critical_patterns = [
            r'main\b',
            r'init\w*',
            r'startup',
            r'login',
            r'auth\w*',
            r'process\w*',
            r'handle\w*',
            r'server\w*',
            r'client\w*'
        ]
        
        # High-impact file patterns
        self.critical_files = [
            r'main\.',
            r'server\.',
            r'client\.',
            r'core\.',
            r'engine\.',
            r'manager\.',
            r'controller\.',
            r'service\.'
        ]
        
        # Low-impact patterns (test code, utilities, etc.)
        self.low_impact_patterns = [
            r'test\w*',
            r'debug\w*',
            r'util\w*',
            r'helper\w*',
            r'example\w*',
            r'demo\w*',
            r'sample\w*'
        ]
    
    def analyze_leak_impact(self, leak: MemoryLeak, frequency_data: Dict[str, int] = None) -> ImpactScore:
        """Analyze the impact of a single memory leak"""
        reasoning = []
        
        # 1. Severity Score (based on leak type)
        severity_score = self._calculate_severity_score(leak, reasoning)
        
        # 2. Size Score (based on memory amount)
        size_score = self._calculate_size_score(leak, reasoning)
        
        # 3. Frequency Score (how often this pattern occurs)
        frequency_score = self._calculate_frequency_score(leak, frequency_data, reasoning)
        
        # 4. Location Score (criticality of code location)
        location_score = self._calculate_location_score(leak, reasoning)
        
        # 5. Type Score (inherent risk of leak type)
        type_score = self._calculate_type_score(leak, reasoning)
        
        # Calculate weighted total score
        weights = {
            'severity': 0.25,
            'size': 0.20,
            'frequency': 0.20,
            'location': 0.20,
            'type': 0.15
        }
        
        total_score = (
            severity_score * weights['severity'] +
            size_score * weights['size'] +
            frequency_score * weights['frequency'] +
            location_score * weights['location'] +
            type_score * weights['type']
        )
        
        # Determine impact category
        category = self._score_to_category(total_score)
        
        return ImpactScore(
            total_score=total_score,
            category=category,
            severity_score=severity_score,
            size_score=size_score,
            frequency_score=frequency_score,
            location_score=location_score,
            type_score=type_score,
            reasoning=reasoning
        )
    
    def _calculate_severity_score(self, leak: MemoryLeak, reasoning: List[str]) -> float:
        """Calculate score based on leak severity"""
        severity = leak.get_severity()
        
        if severity == "HIGH":
            reasoning.append("High severity leak (definitely lost or buffer overflow)")
            return 1.0
        elif severity == "MEDIUM":
            reasoning.append("Medium severity leak (possibly lost or stack overflow)")
            return 0.6
        else:
            reasoning.append("Low severity leak (still reachable or indirect)")
            return 0.2
    
    def _calculate_size_score(self, leak: MemoryLeak, reasoning: List[str]) -> float:
        """Calculate score based on leak size"""
        size = leak.size
        
        if size >= 10000:  # 10KB+
            reasoning.append(f"Very large leak ({size:,} bytes)")
            return 1.0
        elif size >= 1000:  # 1KB+
            reasoning.append(f"Large leak ({size:,} bytes)")
            return 0.8
        elif size >= 100:  # 100B+
            reasoning.append(f"Medium leak ({size:,} bytes)")
            return 0.5
        elif size >= 10:   # 10B+
            reasoning.append(f"Small leak ({size:,} bytes)")
            return 0.3
        else:
            reasoning.append(f"Very small leak ({size:,} bytes)")
            return 0.1
    
    def _calculate_frequency_score(self, leak: MemoryLeak, frequency_data: Dict[str, int], reasoning: List[str]) -> float:
        """Calculate score based on how frequently this pattern occurs"""
        if not frequency_data:
            return 0.5  # Default score when no frequency data
        
        pattern = leak.primary_location
        frequency = frequency_data.get(pattern, 1)
        
        if frequency >= 50:
            reasoning.append(f"Very frequent pattern ({frequency} occurrences)")
            return 1.0
        elif frequency >= 10:
            reasoning.append(f"Frequent pattern ({frequency} occurrences)")
            return 0.8
        elif frequency >= 5:
            reasoning.append(f"Moderate frequency ({frequency} occurrences)")
            return 0.6
        else:
            reasoning.append(f"Infrequent pattern ({frequency} occurrences)")
            return 0.3
    
    def _calculate_location_score(self, leak: MemoryLeak, reasoning: List[str]) -> float:
        """Calculate score based on code location criticality"""
        location_text = leak.primary_location.lower()
        
        # Check stack trace for critical patterns
        for frame in leak.stack_trace:
            frame_text = f"{frame.function} {frame.file or ''}".lower()
            
            # Check for critical patterns
            for pattern in self.critical_patterns:
                if re.search(pattern, frame_text):
                    reasoning.append(f"Critical function: {frame.function}")
                    return 1.0
            
            # Check for critical files
            if frame.file:
                for pattern in self.critical_files:
                    if re.search(pattern, frame.file.lower()):
                        reasoning.append(f"Critical file: {frame.file}")
                        return 0.9
            
            # Check for low-impact patterns
            for pattern in self.low_impact_patterns:
                if re.search(pattern, frame_text):
                    reasoning.append(f"Low-impact location: {frame.function}")
                    return 0.2
        
        # Default score for application code
        reasoning.append("Standard application code")
        return 0.6
    
    def _calculate_type_score(self, leak: MemoryLeak, reasoning: List[str]) -> float:
        """Calculate score based on leak type inherent risk"""
        leak_type = leak.leak_type
        
        if leak_type in [LeakType.HEAP_BUFFER_OVERFLOW, LeakType.USE_AFTER_FREE, LeakType.DOUBLE_FREE]:
            reasoning.append("Critical memory safety issue")
            return 1.0
        elif leak_type == LeakType.DEFINITELY_LOST:
            reasoning.append("Definite memory leak")
            return 0.8
        elif leak_type in [LeakType.STACK_BUFFER_OVERFLOW, LeakType.GLOBAL_BUFFER_OVERFLOW]:
            reasoning.append("Buffer overflow vulnerability")
            return 0.9
        elif leak_type == LeakType.POSSIBLY_LOST:
            reasoning.append("Possible memory leak")
            return 0.5
        elif leak_type == LeakType.INDIRECTLY_LOST:
            reasoning.append("Indirect memory leak")
            return 0.4
        elif leak_type == LeakType.STILL_REACHABLE:
            reasoning.append("Still reachable memory")
            return 0.2
        else:
            return 0.5
    
    def _score_to_category(self, score: float) -> ImpactCategory:
        """Convert numeric score to impact category"""
        if score >= 0.9:
            return ImpactCategory.CRITICAL
        elif score >= 0.7:
            return ImpactCategory.HIGH
        elif score >= 0.5:
            return ImpactCategory.MEDIUM
        elif score >= 0.3:
            return ImpactCategory.LOW
        else:
            return ImpactCategory.NEGLIGIBLE
    
    def analyze_database_impact(self, leak_db: LeakDatabase) -> Dict[str, Any]:
        """Analyze impact for entire leak database"""
        leaks = leak_db.get_all_leaks()
        
        if not leaks:
            return {"status": "no_data"}
        
        # Calculate frequency data
        frequency_data = {}
        for leak in leaks:
            pattern = leak.primary_location
            frequency_data[pattern] = frequency_data.get(pattern, 0) + 1
        
        # Analyze each leak
        scored_leaks = []
        for leak in leaks:
            impact = self.analyze_leak_impact(leak, frequency_data)
            scored_leaks.append((leak, impact))
        
        # Sort by impact score (highest first)
        scored_leaks.sort(key=lambda x: x[1].total_score, reverse=True)
        
        # Calculate summary statistics
        category_counts = {}
        for _, impact in scored_leaks:
            cat = impact.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Get top issues
        top_issues = scored_leaks[:10]
        
        # Calculate overall risk score
        total_impact = sum(impact.total_score for _, impact in scored_leaks)
        avg_impact = total_impact / len(scored_leaks)
        
        return {
            "status": "success",
            "total_leaks": len(leaks),
            "avg_impact_score": avg_impact,
            "category_breakdown": category_counts,
            "top_issues": [(leak, impact) for leak, impact in top_issues],
            "all_scored_leaks": scored_leaks
        }
    
    def generate_priority_report(self, leak_db: LeakDatabase) -> str:
        """Generate a prioritized report of memory leaks"""
        analysis = self.analyze_database_impact(leak_db)
        
        if analysis["status"] != "success":
            return "No leaks to analyze."
        
        report = ["MEMORY LEAK IMPACT ANALYSIS REPORT"]
        report.append("=" * 50)
        report.append(f"Total Leaks Analyzed: {analysis['total_leaks']}")
        report.append(f"Average Impact Score: {analysis['avg_impact_score']:.2f}")
        report.append("")
        
        report.append("IMPACT CATEGORY BREAKDOWN:")
        for category, count in analysis['category_breakdown'].items():
            percentage = (count / analysis['total_leaks']) * 100
            report.append(f"  {category.upper():12}: {count:3d} ({percentage:5.1f}%)")
        report.append("")
        
        report.append("TOP PRIORITY ISSUES:")
        report.append("-" * 30)
        
        for i, (leak, impact) in enumerate(analysis['top_issues'], 1):
            report.append(f"{i:2d}. [{impact.category.value.upper()}] Score: {impact.total_score:.2f}")
            report.append(f"    Type: {leak.leak_type.value.replace('_', ' ').title()}")
            report.append(f"    Size: {leak.size:,} bytes")
            report.append(f"    Location: {leak.primary_location}")
            
            # Show top reasons
            if impact.reasoning:
                report.append(f"    Reasons: {'; '.join(impact.reasoning[:2])}")
            report.append("")
        
        return "\n".join(report)
    
    def get_recommendations(self, leak_db: LeakDatabase) -> List[str]:
        """Get prioritized recommendations for fixing leaks"""
        analysis = self.analyze_database_impact(leak_db)
        
        if analysis["status"] != "success":
            return ["No leaks found to analyze."]
        
        recommendations = []
        category_counts = analysis['category_breakdown']
        
        # Critical issues
        if category_counts.get('critical', 0) > 0:
            recommendations.append(
                f"🚨 URGENT: Fix {category_counts['critical']} critical memory safety issues immediately. "
                "These represent serious security vulnerabilities."
            )
        
        # High impact issues
        if category_counts.get('high', 0) > 0:
            recommendations.append(
                f"⚠️  HIGH PRIORITY: Address {category_counts['high']} high-impact leaks. "
                "These are causing significant memory loss."
            )
        
        # Pattern analysis
        top_issues = analysis['top_issues'][:3]
        if top_issues:
            file_patterns = {}
            for leak, impact in top_issues:
                for frame in leak.stack_trace:
                    if frame.file:
                        file_patterns[frame.file] = file_patterns.get(frame.file, 0) + 1
            
            if file_patterns:
                most_problematic = max(file_patterns, key=file_patterns.get)
                recommendations.append(
                    f"📁 Focus on {most_problematic} - appears in {file_patterns[most_problematic]} "
                    "high-impact leaks."
                )
        
        # Size-based recommendations
        large_leaks = [leak for leak, impact in analysis['all_scored_leaks'] if leak.size >= 1000]
        if large_leaks:
            total_large_bytes = sum(leak.size for leak in large_leaks)
            recommendations.append(
                f"💾 Target {len(large_leaks)} large leaks (1KB+) - would free {total_large_bytes:,} bytes."
            )
        
        return recommendations 