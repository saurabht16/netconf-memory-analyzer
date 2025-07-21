"""
Data models for memory leak information
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class LeakType(Enum):
    DEFINITELY_LOST = "definitely_lost"
    INDIRECTLY_LOST = "indirectly_lost"
    POSSIBLY_LOST = "possibly_lost"
    STILL_REACHABLE = "still_reachable"
    HEAP_BUFFER_OVERFLOW = "heap_buffer_overflow"
    STACK_BUFFER_OVERFLOW = "stack_buffer_overflow"
    GLOBAL_BUFFER_OVERFLOW = "global_buffer_overflow"
    USE_AFTER_FREE = "use_after_free"
    DOUBLE_FREE = "double_free"
    OTHER = "other"


@dataclass
class StackFrame:
    function: str
    file: Optional[str] = None
    line: Optional[int] = None
    address: Optional[str] = None
    
    def __str__(self):
        if self.file and self.line:
            return f"{self.function} ({self.file}:{self.line})"
        elif self.file:
            return f"{self.function} ({self.file})"
        else:
            return self.function


@dataclass
class MemoryLeak:
    leak_type: LeakType
    size: int
    count: int
    stack_trace: List[StackFrame]
    location: str
    message: str = ""
    source_file: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    @property
    def primary_location(self) -> str:
        """Get the primary location where the leak occurred"""
        if self.stack_trace:
            frame = self.stack_trace[0]
            return str(frame)
        return self.location
    
    def get_severity(self) -> str:
        """Get severity level of the leak"""
        if self.leak_type in [LeakType.DEFINITELY_LOST, LeakType.HEAP_BUFFER_OVERFLOW, 
                             LeakType.USE_AFTER_FREE, LeakType.DOUBLE_FREE]:
            return "HIGH"
        elif self.leak_type in [LeakType.POSSIBLY_LOST, LeakType.STACK_BUFFER_OVERFLOW,
                               LeakType.GLOBAL_BUFFER_OVERFLOW]:
            return "MEDIUM"
        else:
            return "LOW"


class LeakDatabase:
    """Database to store and manage memory leaks"""
    
    def __init__(self):
        self.leaks: List[MemoryLeak] = []
        self._stats_cache: Optional[Dict[str, Any]] = None
    
    def add_leak(self, leak: MemoryLeak):
        """Add a single leak to the database"""
        self.leaks.append(leak)
        self._invalidate_cache()
    
    def add_leaks(self, leaks: List[MemoryLeak]):
        """Add multiple leaks to the database"""
        self.leaks.extend(leaks)
        self._invalidate_cache()
    
    def get_all_leaks(self) -> List[MemoryLeak]:
        """Get all leaks"""
        return self.leaks.copy()
    
    def get_leaks_by_type(self, leak_type: LeakType) -> List[MemoryLeak]:
        """Get leaks filtered by type"""
        return [leak for leak in self.leaks if leak.leak_type == leak_type]
    
    def get_leaks_by_severity(self, severity: str) -> List[MemoryLeak]:
        """Get leaks filtered by severity"""
        return [leak for leak in self.leaks if leak.get_severity() == severity]
    
    def filter_leaks(self, 
                    file_pattern: Optional[str] = None,
                    directory_pattern: Optional[str] = None,
                    function_pattern: Optional[str] = None,
                    leak_types: Optional[List[LeakType]] = None,
                    severities: Optional[List[str]] = None,
                    min_size: Optional[int] = None,
                    max_size: Optional[int] = None) -> List[MemoryLeak]:
        """Filter leaks based on various criteria"""
        filtered_leaks = self.leaks.copy()
        
        if file_pattern:
            file_pattern = file_pattern.lower()
            filtered_leaks = [leak for leak in filtered_leaks 
                            if any(frame.file and file_pattern in frame.file.lower() 
                                 for frame in leak.stack_trace)]
        
        if directory_pattern:
            directory_pattern = directory_pattern.lower()
            filtered_leaks = [leak for leak in filtered_leaks 
                            if any(frame.file and directory_pattern in frame.file.lower() 
                                 for frame in leak.stack_trace)]
        
        if function_pattern:
            function_pattern = function_pattern.lower()
            filtered_leaks = [leak for leak in filtered_leaks 
                            if any(function_pattern in frame.function.lower() 
                                 for frame in leak.stack_trace)]
        
        if leak_types:
            filtered_leaks = [leak for leak in filtered_leaks if leak.leak_type in leak_types]
        
        if severities:
            filtered_leaks = [leak for leak in filtered_leaks if leak.get_severity() in severities]
        
        if min_size is not None:
            filtered_leaks = [leak for leak in filtered_leaks if leak.size >= min_size]
        
        if max_size is not None:
            filtered_leaks = [leak for leak in filtered_leaks if leak.size <= max_size]
        
        return filtered_leaks
    
    def search_leaks(self, search_term: str) -> List[MemoryLeak]:
        """Search leaks by any text content"""
        search_term = search_term.lower()
        return [leak for leak in self.leaks 
                if (search_term in leak.message.lower() or
                    search_term in leak.location.lower() or
                    any(search_term in frame.function.lower() for frame in leak.stack_trace) or
                    any(frame.file and search_term in frame.file.lower() for frame in leak.stack_trace))]
    
    def cleanup_leaks(self,
                     remove_system_libs: bool = True,
                     remove_third_party: bool = True, 
                     min_leak_size: int = 8,
                     remove_incomplete_traces: bool = True,
                     remove_reachable: bool = False,
                     custom_exclude_patterns: Optional[List[str]] = None) -> List[MemoryLeak]:
        """Clean up leaks by removing unwanted/irrelevant entries"""
        
        # Default system library patterns
        system_patterns = [
            '/lib/', '/lib64/', '/usr/lib/', '/usr/lib64/',
            '/lib/x86_64-linux-gnu/', '/usr/lib/x86_64-linux-gnu/',
            'libc.so', 'libpthread.so', 'libdl.so', 'libm.so',
            'libX11.so', 'libGL.so', 'libgcc_s.so',
            '/System/Library/', '/usr/lib/system/',  # macOS
            'libsystem_', 'libobjc.', 'CoreFoundation'  # macOS
        ]
        
        # Third-party library patterns  
        third_party_patterns = [
            'libssl.so', 'libcrypto.so', 'libcurl.so',
            'libpng.so', 'libjpeg.so', 'libz.so',
            'libffi.so', 'libglib.so', 'libgtk.so',
            'Qt5', 'libboost', 'libstdc++.so'
        ]
        
        exclude_patterns = []
        if remove_system_libs:
            exclude_patterns.extend(system_patterns)
        if remove_third_party:
            exclude_patterns.extend(third_party_patterns)
        if custom_exclude_patterns:
            exclude_patterns.extend(custom_exclude_patterns)
        
        cleaned_leaks = []
        
        for leak in self.leaks:
            # Skip if too small
            if leak.size < min_leak_size:
                continue
            
            # Skip reachable memory if requested
            if remove_reachable and leak.leak_type == LeakType.STILL_REACHABLE:
                continue
            
            # Skip incomplete traces if requested
            if remove_incomplete_traces and len(leak.stack_trace) == 0:
                continue
            
            # Check if leak is in excluded libraries
            is_excluded = False
            for pattern in exclude_patterns:
                if any(frame.file and pattern in frame.file for frame in leak.stack_trace):
                    is_excluded = True
                    break
                if any(pattern in frame.function for frame in leak.stack_trace):
                    is_excluded = True
                    break
            
            if not is_excluded:
                cleaned_leaks.append(leak)
        
        return cleaned_leaks
    
    def group_similar_leaks(self, leaks: Optional[List[MemoryLeak]] = None) -> Dict[str, List[MemoryLeak]]:
        """Group leaks with similar stack traces"""
        if leaks is None:
            leaks = self.leaks
        
        groups = {}
        
        for leak in leaks:
            # Create a signature from the top few stack frames
            signature_frames = []
            for frame in leak.stack_trace[:3]:  # Use top 3 frames
                if frame.function != "Unknown":
                    signature_frames.append(frame.function)
            
            signature = " -> ".join(signature_frames) if signature_frames else "Unknown"
            
            if signature not in groups:
                groups[signature] = []
            groups[signature].append(leak)
        
        return groups
    
    def get_cleanup_stats(self, cleaned_leaks: List[MemoryLeak]) -> Dict[str, Any]:
        """Get statistics about what was cleaned up"""
        original_count = len(self.leaks)
        cleaned_count = len(cleaned_leaks)
        removed_count = original_count - cleaned_count
        
        original_bytes = sum(leak.size for leak in self.leaks)
        cleaned_bytes = sum(leak.size for leak in cleaned_leaks)
        removed_bytes = original_bytes - cleaned_bytes
        
        return {
            'original_count': original_count,
            'cleaned_count': cleaned_count,
            'removed_count': removed_count,
            'original_bytes': original_bytes,
            'cleaned_bytes': cleaned_bytes,
            'removed_bytes': removed_bytes,
            'removal_percentage': (removed_count / original_count * 100) if original_count > 0 else 0
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the leaks"""
        if self._stats_cache is None:
            self._compute_statistics()
        return self._stats_cache
    
    def _compute_statistics(self):
        """Compute and cache statistics"""
        total_leaks = len(self.leaks)
        total_bytes = sum(leak.size for leak in self.leaks)
        
        # Group by type
        by_type = {}
        for leak in self.leaks:
            leak_type = leak.leak_type.value
            if leak_type not in by_type:
                by_type[leak_type] = {'count': 0, 'bytes': 0}
            by_type[leak_type]['count'] += leak.count
            by_type[leak_type]['bytes'] += leak.size
        
        # Group by severity
        by_severity = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for leak in self.leaks:
            by_severity[leak.get_severity()] += 1
        
        # Top locations
        location_counts = {}
        for leak in self.leaks:
            loc = leak.primary_location
            location_counts[loc] = location_counts.get(loc, 0) + 1
        
        top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        self._stats_cache = {
            'total_leaks': total_leaks,
            'total_bytes': total_bytes,
            'by_type': by_type,
            'by_severity': by_severity,
            'top_locations': top_locations
        }
    
    def _invalidate_cache(self):
        """Invalidate the statistics cache"""
        self._stats_cache = None
    
    def clear(self):
        """Clear all leaks"""
        self.leaks.clear()
        self._invalidate_cache() 