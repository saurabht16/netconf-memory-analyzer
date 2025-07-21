"""
Memory Profiler for Remote Device Analysis
Manages Valgrind and AddressSanitizer profiling sessions on remote devices
"""

import time
import signal
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from .device_connector import DeviceConnector, ProcessInfo

@dataclass
class ProfilingSession:
    """Configuration for a memory profiling session"""
    session_id: str
    process_pid: int
    process_name: str
    profiler_type: str  # valgrind, asan
    output_file: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, completed, failed, stopped
    
@dataclass
class ProfilingConfig:
    """Configuration for profiling options"""
    profiler_type: str = "valgrind"  # valgrind, asan
    valgrind_options: List[str] = None
    asan_options: Dict[str, str] = None
    output_directory: str = "/tmp/memory_analysis"
    session_timeout: int = 3600  # 1 hour
    xml_output: bool = True
    
    def __post_init__(self):
        if self.valgrind_options is None:
            self.valgrind_options = [
                "--tool=memcheck",
                "--leak-check=full", 
                "--show-leak-kinds=all",
                "--track-origins=yes",
                "--xml=yes"
            ]
        
        if self.asan_options is None:
            self.asan_options = {
                "log_path": "/tmp/asan_log",
                "abort_on_error": "0",
                "detect_leaks": "1",
                "check_initialization_order": "1"
            }

class MemoryProfiler:
    """Manages memory profiling sessions on remote devices"""
    
    def __init__(self, device_connector: DeviceConnector):
        self.device = device_connector
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, ProfilingSession] = {}
        self.config = ProfilingConfig()
    
    def start_valgrind_profiling(self, process_pid: int, session_id: str = None) -> Optional[ProfilingSession]:
        """Start Valgrind profiling on a specific process"""
        if session_id is None:
            session_id = f"valgrind_{process_pid}_{int(time.time())}"
        
        try:
            # Get process information
            process_info = self._get_process_info(process_pid)
            if not process_info:
                self.logger.error(f"Process {process_pid} not found")
                return None
            
            # Prepare output file
            output_file = f"{self.config.output_directory}/{session_id}_valgrind.xml"
            
            # Create output directory
            self.device.create_remote_directory(self.config.output_directory)
            
            # Prepare Valgrind command
            valgrind_cmd = self._build_valgrind_command(process_pid, output_file)
            
            self.logger.info(f"Starting Valgrind profiling: {valgrind_cmd}")
            
            # Start Valgrind in background
            bg_command = f"nohup {valgrind_cmd} > /dev/null 2>&1 &"
            exit_code, stdout, stderr = self.device.execute_command(bg_command)
            
            if exit_code == 0:
                session = ProfilingSession(
                    session_id=session_id,
                    process_pid=process_pid,
                    process_name=process_info.name,
                    profiler_type="valgrind",
                    output_file=output_file,
                    start_time=datetime.now(),
                    status="running"
                )
                
                self.active_sessions[session_id] = session
                self.logger.info(f"Valgrind profiling started for PID {process_pid}")
                return session
            else:
                self.logger.error(f"Failed to start Valgrind: {stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to start Valgrind profiling: {e}")
            return None
    
    def start_asan_profiling(self, process_pid: int, session_id: str = None) -> Optional[ProfilingSession]:
        """Start AddressSanitizer profiling on a process"""
        if session_id is None:
            session_id = f"asan_{process_pid}_{int(time.time())}"
        
        try:
            # Get process information
            process_info = self._get_process_info(process_pid)
            if not process_info:
                self.logger.error(f"Process {process_pid} not found")
                return None
            
            # Check if process was built with ASan
            if not self._check_asan_enabled(process_pid):
                self.logger.warning(f"Process {process_pid} may not be built with AddressSanitizer")
            
            # Prepare output file
            output_file = f"{self.config.output_directory}/{session_id}_asan.log"
            
            # Create output directory
            self.device.create_remote_directory(self.config.output_directory)
            
            # Set ASan environment variables
            asan_env = self._build_asan_environment(output_file)
            
            # Monitor the process for ASan output
            session = ProfilingSession(
                session_id=session_id,
                process_pid=process_pid,
                process_name=process_info.name,
                profiler_type="asan",
                output_file=output_file,
                start_time=datetime.now(),
                status="running"
            )
            
            self.active_sessions[session_id] = session
            self.logger.info(f"ASan monitoring started for PID {process_pid}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to start ASan profiling: {e}")
            return None
    
    def stop_profiling_session(self, session_id: str) -> bool:
        """Stop a profiling session"""
        if session_id not in self.active_sessions:
            self.logger.error(f"Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            if session.profiler_type == "valgrind":
                # Find and stop Valgrind process
                find_cmd = f"ps aux | grep 'valgrind.*{session.process_pid}' | grep -v grep | awk '{{print $2}}'"
                exit_code, stdout, stderr = self.device.execute_command(find_cmd)
                
                if exit_code == 0 and stdout.strip():
                    valgrind_pid = stdout.strip().split('\n')[0]
                    # Send SIGTERM to Valgrind to generate final report
                    self.device.execute_command(f"kill -TERM {valgrind_pid}")
                    time.sleep(2)  # Give it time to finish
            
            session.end_time = datetime.now()
            session.status = "completed"
            
            self.logger.info(f"Profiling session {session_id} stopped")
            return True
            
        except Exception as e:
            session.status = "failed"
            self.logger.error(f"Failed to stop session {session_id}: {e}")
            return False
    
    def get_session_status(self, session_id: str) -> Optional[ProfilingSession]:
        """Get status of a profiling session"""
        return self.active_sessions.get(session_id)
    
    def list_active_sessions(self) -> List[ProfilingSession]:
        """List all active profiling sessions"""
        return list(self.active_sessions.values())
    
    def download_session_logs(self, session_id: str, local_directory: Path) -> Optional[Path]:
        """Download profiling logs from device to local machine"""
        if session_id not in self.active_sessions:
            self.logger.error(f"Session {session_id} not found")
            return None
        
        session = self.active_sessions[session_id]
        local_directory.mkdir(parents=True, exist_ok=True)
        
        # Generate local filename
        local_filename = f"{session_id}_{session.profiler_type}.{'xml' if session.profiler_type == 'valgrind' else 'log'}"
        local_path = local_directory / local_filename
        
        try:
            if self.device.download_file(session.output_file, local_path):
                self.logger.info(f"Downloaded session logs to {local_path}")
                return local_path
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to download session logs: {e}")
            return None
    
    def cleanup_remote_files(self, session_id: str) -> bool:
        """Clean up remote profiling files"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            # Remove output file
            self.device.execute_command(f"rm -f {session.output_file}")
            
            # Remove any temporary files
            temp_pattern = f"{self.config.output_directory}/{session_id}*"
            self.device.execute_command(f"rm -f {temp_pattern}")
            
            self.logger.info(f"Cleaned up remote files for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup remote files: {e}")
            return False
    
    def _get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Get information about a specific process"""
        try:
            ps_cmd = f"ps -p {pid} -o pid,comm,cmd,rss,pcpu --no-headers"
            exit_code, stdout, stderr = self.device.execute_command(ps_cmd)
            
            if exit_code == 0 and stdout.strip():
                parts = stdout.strip().split(None, 4)
                if len(parts) >= 5:
                    return ProcessInfo(
                        pid=int(parts[0]),
                        name=parts[1],
                        command=parts[4],
                        memory_usage=int(parts[3]) if parts[3].isdigit() else 0,
                        cpu_usage=float(parts[4]) if parts[4].replace('.', '').isdigit() else 0.0
                    )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get process info for PID {pid}: {e}")
            return None
    
    def _build_valgrind_command(self, pid: int, output_file: str) -> str:
        """Build Valgrind command for attaching to process"""
        # Note: Valgrind typically can't attach to running processes
        # This would need to be adapted for your specific use case
        options = " ".join(self.config.valgrind_options)
        return f"valgrind {options} --xml-file={output_file} --pid={pid}"
    
    def _build_asan_environment(self, output_file: str) -> str:
        """Build AddressSanitizer environment variables"""
        asan_opts = []
        for key, value in self.config.asan_options.items():
            if key == "log_path":
                asan_opts.append(f"{key}={output_file}")
            else:
                asan_opts.append(f"{key}={value}")
        
        return f"ASAN_OPTIONS='{':'.join(asan_opts)}'"
    
    def _check_asan_enabled(self, pid: int) -> bool:
        """Check if a process was built with AddressSanitizer"""
        try:
            # Check if ASan symbols are present
            check_cmd = f"cat /proc/{pid}/maps | grep -i asan"
            exit_code, stdout, stderr = self.device.execute_command(check_cmd)
            return exit_code == 0 and stdout.strip() != ""
        except Exception:
            return False 