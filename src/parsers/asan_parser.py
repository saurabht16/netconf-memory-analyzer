"""
AddressSanitizer (ASan) log file parser
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from ..models.leak_data import MemoryLeak, StackFrame, LeakType


class AsanParser:
    """Parser for AddressSanitizer log files"""
    
    def __init__(self):
        # Regex patterns for different ASan error types
        self.error_patterns = {
            LeakType.HEAP_BUFFER_OVERFLOW: [
                r'heap-buffer-overflow',
                r'heap buffer overflow',
                r'AddressSanitizer: heap-buffer-overflow'
            ],
            LeakType.STACK_BUFFER_OVERFLOW: [
                r'stack-buffer-overflow',
                r'stack buffer overflow',
                r'AddressSanitizer: stack-buffer-overflow'
            ],
            LeakType.GLOBAL_BUFFER_OVERFLOW: [
                r'global-buffer-overflow',
                r'global buffer overflow',
                r'AddressSanitizer: global-buffer-overflow'
            ],
            LeakType.USE_AFTER_FREE: [
                r'heap-use-after-free',
                r'use-after-free',
                r'AddressSanitizer: heap-use-after-free'
            ],
            LeakType.DOUBLE_FREE: [
                r'attempting free on address which was already freed',
                r'double-free',
                r'AddressSanitizer: attempting free'
            ]
        }
        
        # Regex for parsing stack frames
        self.frame_pattern = re.compile(
            r'#(\d+)\s+(0x[0-9a-fA-F]+)\s+in\s+(.+?)\s+(.*?)(?::(\d+))?(?::(\d+))?$'
        )
        
        # Alternative frame pattern
        self.frame_pattern2 = re.compile(
            r'#(\d+)\s+(0x[0-9a-fA-F]+)\s+(.+?)\s+(.*?)(?::(\d+))?$'
        )
        
        # Memory leak pattern (for leak detection mode)
        self.leak_pattern = re.compile(
            r'Direct leak of (\d+) byte\(s\) in (\d+) object\(s\) allocated from:'
        )
        
        # Size pattern for buffer overflows
        self.size_pattern = re.compile(r'(\d+) bytes')
    
    def parse_file(self, file_path: Path) -> List[MemoryLeak]:
        """Parse an ASan log file and return a list of memory errors"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            leaks = []
            
            # Split content into error blocks
            error_blocks = self._split_into_error_blocks(content)
            
            for block in error_blocks:
                leak = self._parse_error_block(block)
                if leak:
                    leak.source_file = str(file_path)
                    leak.timestamp = datetime.now()
                    leaks.append(leak)
            
            return leaks
            
        except Exception as e:
            raise ValueError(f"Error parsing ASan file: {e}")
    
    def _split_into_error_blocks(self, content: str) -> List[str]:
        """Split ASan log content into individual error blocks"""
        # ASan errors typically start with "==PID==ERROR:" or similar
        error_start_pattern = re.compile(r'==\d+==ERROR:.*?AddressSanitizer')
        
        blocks = []
        lines = content.split('\n')
        current_block = []
        in_error_block = False
        
        for line in lines:
            if error_start_pattern.search(line):
                if current_block and in_error_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
                in_error_block = True
            elif in_error_block:
                current_block.append(line)
                # End block on empty line or start of summary
                if not line.strip() and len(current_block) > 5:
                    # Check if this looks like end of error
                    if any(keyword in line for keyword in ['SUMMARY:', 'ABORTING']):
                        blocks.append('\n'.join(current_block))
                        current_block = []
                        in_error_block = False
        
        # Add the last block if it exists
        if current_block and in_error_block:
            blocks.append('\n'.join(current_block))
        
        # Also look for leak detection reports
        leak_blocks = self._extract_leak_blocks(content)
        blocks.extend(leak_blocks)
        
        return blocks
    
    def _extract_leak_blocks(self, content: str) -> List[str]:
        """Extract leak detection blocks from ASan output"""
        leak_blocks = []
        lines = content.split('\n')
        current_block = []
        in_leak_block = False
        
        for line in lines:
            if 'Direct leak of' in line or 'Indirect leak of' in line:
                if current_block and in_leak_block:
                    leak_blocks.append('\n'.join(current_block))
                current_block = [line]
                in_leak_block = True
            elif in_leak_block:
                current_block.append(line)
                if line.strip() == '' and len(current_block) > 3:
                    # Check if next non-empty line starts a new leak or summary
                    peek_ahead = False
                    for next_line in lines[lines.index(line)+1:lines.index(line)+5]:
                        if next_line.strip():
                            if ('leak of' in next_line or 
                                'SUMMARY:' in next_line or 
                                'ABORTING' in next_line):
                                peek_ahead = True
                            break
                    if peek_ahead:
                        leak_blocks.append('\n'.join(current_block))
                        current_block = []
                        in_leak_block = False
        
        if current_block and in_leak_block:
            leak_blocks.append('\n'.join(current_block))
        
        return leak_blocks
    
    def _parse_error_block(self, block: str) -> Optional[MemoryLeak]:
        """Parse a single error block from ASan output"""
        lines = block.split('\n')
        
        # Detect error type
        leak_type = self._detect_error_type(block)
        
        # Extract size and count information
        size, count = self._extract_size_info(block)
        
        # Extract message (first line usually contains the error description)
        message = ""
        for line in lines:
            if 'AddressSanitizer:' in line or 'ERROR:' in line:
                message = line.strip()
                break
        
        # Parse stack trace
        stack_trace = self._parse_stack_trace_from_block(block)
        
        # Determine location
        location = "Unknown"
        if stack_trace:
            location = str(stack_trace[0])
        elif message:
            location = message[:100]  # Use first part of message as location
        
        return MemoryLeak(
            leak_type=leak_type,
            size=size,
            count=count,
            stack_trace=stack_trace,
            location=location,
            message=message
        )
    
    def _detect_error_type(self, block: str) -> LeakType:
        """Detect the type of ASan error from the block content"""
        block_lower = block.lower()
        
        for leak_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, block_lower):
                    return leak_type
        
        # Check for leak detection patterns
        if 'direct leak of' in block_lower:
            return LeakType.DEFINITELY_LOST
        elif 'indirect leak of' in block_lower:
            return LeakType.INDIRECTLY_LOST
        
        return LeakType.OTHER
    
    def _extract_size_info(self, block: str) -> Tuple[int, int]:
        """Extract size and count information from ASan error block"""
        size = 0
        count = 1
        
        # Look for leak size pattern
        leak_match = self.leak_pattern.search(block)
        if leak_match:
            size = int(leak_match.group(1))
            count = int(leak_match.group(2))
            return size, count
        
        # Look for general size patterns
        size_matches = self.size_pattern.findall(block)
        if size_matches:
            # Take the largest size found
            sizes = [int(s) for s in size_matches]
            size = max(sizes)
        
        return size, count
    
    def _parse_stack_trace_from_block(self, block: str) -> List[StackFrame]:
        """Parse stack trace from ASan error block"""
        stack_trace = []
        lines = block.split('\n')
        
        for line in lines:
            frame = self._parse_stack_frame(line.strip())
            if frame:
                stack_trace.append(frame)
        
        return stack_trace
    
    def _parse_stack_frame(self, line: str) -> Optional[StackFrame]:
        """Parse a single stack frame line"""
        # Try the first pattern
        match = self.frame_pattern.match(line)
        if not match:
            # Try the alternative pattern
            match = self.frame_pattern2.match(line)
        
        if match:
            if len(match.groups()) >= 4:
                address = match.group(2)
                function = match.group(3)
                location_info = match.group(4)
                
                # Parse file and line from location_info
                file_name = None
                line_num = None
                
                if ':' in location_info:
                    parts = location_info.split(':')
                    if len(parts) >= 2:
                        file_name = parts[0]
                        try:
                            line_num = int(parts[1])
                        except ValueError:
                            pass
                
                return StackFrame(
                    function=function,
                    file=file_name,
                    line=line_num,
                    address=address
                )
        
        return None
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate if the file is a valid ASan log file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first few lines to check for ASan markers
                first_lines = []
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    first_lines.append(line.lower())
                
                content = ''.join(first_lines)
                
                # Check for ASan signatures
                asan_markers = [
                    'addresssanitizer',
                    'asan',
                    'heap-buffer-overflow',
                    'stack-buffer-overflow',
                    'heap-use-after-free',
                    'direct leak of',
                    'indirect leak of'
                ]
                
                return any(marker in content for marker in asan_markers)
                
        except Exception:
            return False 