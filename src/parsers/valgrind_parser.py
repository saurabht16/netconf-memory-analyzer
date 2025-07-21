"""
Valgrind XML file parser
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models.leak_data import MemoryLeak, StackFrame, LeakType


class ValgrindParser:
    """Parser for Valgrind XML output files"""
    
    def __init__(self):
        self.leak_type_mapping = {
            'Leak_DefinitelyLost': LeakType.DEFINITELY_LOST,
            'Leak_IndirectlyLost': LeakType.INDIRECTLY_LOST,
            'Leak_PossiblyLost': LeakType.POSSIBLY_LOST,
            'Leak_StillReachable': LeakType.STILL_REACHABLE,
        }
    
    def parse_file(self, file_path: Path, skip_suppressed: bool = True) -> List[MemoryLeak]:
        """Parse a Valgrind XML file and return a list of memory leaks"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            leaks = []
            suppressed_count = 0
            
            # Find all error elements
            for error in root.findall('.//error'):
                # Check if error is suppressed
                suppressed = error.find('suppression')
                if suppressed is not None and skip_suppressed:
                    suppressed_count += 1
                    continue
                
                leak = self._parse_error_element(error)
                if leak:
                    leak.source_file = str(file_path)
                    leak.timestamp = datetime.now()
                    leaks.append(leak)
            
            if suppressed_count > 0:
                print(f"Note: Skipped {suppressed_count} suppressed errors")
            
            return leaks
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing Valgrind file: {e}")
    
    def _parse_error_element(self, error_elem) -> Optional[MemoryLeak]:
        """Parse a single error element from Valgrind XML"""
        kind_elem = error_elem.find('kind')
        if kind_elem is None:
            return None
        
        kind = kind_elem.text
        leak_type = self.leak_type_mapping.get(kind, LeakType.OTHER)
        
        # Extract size information
        size = 0
        count = 1
        
        # Look for leak size in various places
        xwhat_elem = error_elem.find('xwhat')
        if xwhat_elem is not None:
            leakedbytes_elem = xwhat_elem.find('leakedbytes')
            if leakedbytes_elem is not None:
                size = int(leakedbytes_elem.text)
            
            leakedblocks_elem = xwhat_elem.find('leakedblocks')
            if leakedblocks_elem is not None:
                count = int(leakedblocks_elem.text)
        
        # Extract message
        what_elem = error_elem.find('what')
        message = what_elem.text if what_elem is not None else ""
        
        # Extract stack trace
        stack_trace = self._parse_stack_trace(error_elem)
        
        # Determine location
        location = "Unknown"
        if stack_trace:
            location = str(stack_trace[0])
        
        return MemoryLeak(
            leak_type=leak_type,
            size=size,
            count=count,
            stack_trace=stack_trace,
            location=location,
            message=message
        )
    
    def _parse_stack_trace(self, error_elem) -> List[StackFrame]:
        """Parse stack trace from error element"""
        stack_trace = []
        
        stack_elem = error_elem.find('stack')
        if stack_elem is not None:
            for frame in stack_elem.findall('frame'):
                fn_elem = frame.find('fn')
                file_elem = frame.find('file')
                line_elem = frame.find('line')
                ip_elem = frame.find('ip')
                
                function = fn_elem.text if fn_elem is not None else "Unknown"
                file_name = file_elem.text if file_elem is not None else None
                line_num = int(line_elem.text) if line_elem is not None else None
                address = ip_elem.text if ip_elem is not None else None
                
                stack_frame = StackFrame(
                    function=function,
                    file=file_name,
                    line=line_num,
                    address=address
                )
                stack_trace.append(stack_frame)
        
        return stack_trace
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate if the file is a valid Valgrind XML file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Check if it's a Valgrind XML file
            if root.tag == 'valgrindoutput':
                return True
            
            # Also check for common Valgrind elements
            if root.find('.//error') is not None:
                return True
                
            return False
            
        except ET.ParseError:
            return False
        except Exception:
            return False 