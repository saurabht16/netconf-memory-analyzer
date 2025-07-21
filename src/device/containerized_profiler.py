"""
Containerized Memory Profiler
Specialized profiler for Docker containerized NETCONF applications
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from .device_connector import DeviceConnector, ProcessInfo
from .docker_manager import DockerManager, ContainerInfo, ContainerConfig
from .memory_profiler import ProfilingSession, ProfilingConfig

@dataclass
class ContainerProfilingSession:
    """Profiling session for containerized applications"""
    session_id: str
    container_id: str
    container_name: str
    process_pid: int
    process_name: str
    profiler_type: str
    output_file: str
    container_output_file: str
    start_time: datetime
    memory_increased: bool = False
    original_memory_limit: str = ""
    new_memory_limit: str = ""
    end_time: Optional[datetime] = None
    status: str = "running"

class ContainerizedProfiler:
    """Memory profiler for containerized applications"""
    
    def __init__(self, device_connector: DeviceConnector):
        self.device = device_connector
        self.docker = DockerManager(device_connector)
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, ContainerProfilingSession] = {}
        
    def discover_containers_and_processes(self) -> Dict[str, List[ProcessInfo]]:
        """Discover NETCONF containers and their processes"""
        containers = self.docker.find_netconf_containers()
        result = {}
        
        for container in containers:
            processes = self.docker.find_netconf_processes_in_container(container.container_id)
            if processes:
                result[f"{container.name} ({container.container_id[:12]})"] = {
                    'container': container,
                    'processes': processes
                }
        
        return result
    
    def start_containerized_profiling(self, 
                                     container_id: str,
                                     process_pid: int,
                                     memory_limit: str = "5g",
                                     profiler_type: str = "valgrind",
                                     session_id: str = None) -> Optional[ContainerProfilingSession]:
        """Start memory profiling in a containerized environment"""
        
        if session_id is None:
            session_id = f"container_{container_id[:8]}_{process_pid}_{int(time.time())}"
        
        try:
            self.logger.info(f"Starting containerized profiling session: {session_id}")
            
            # Get container info
            containers = self.docker.list_containers()
            container = next((c for c in containers if c.container_id.startswith(container_id)), None)
            
            if not container:
                self.logger.error(f"Container {container_id} not found")
                return None
            
            # Get current memory limit
            original_memory = container.memory_limit
            
            # Step 1: Increase container memory
            self.logger.info(f"Step 1: Increasing container memory from {original_memory} to {memory_limit}")
            container_config = ContainerConfig(
                container_id=container_id,
                memory_limit=memory_limit,
                restart_required=False  # No restart needed for memory update
            )
            
            memory_increased = self.docker.increase_container_memory(container_id, memory_limit, container_config)
            if not memory_increased:
                self.logger.error("Failed to increase container memory")
                return None
            
            # Step 2: Verify processes are still available (no restart, so PIDs should be stable)
            self.logger.info("Step 2: Verifying process availability...")
            time.sleep(2)  # Brief wait for memory update to take effect
            
            # Verify process still exists
            processes = self.docker.get_container_processes(container_id)
            target_process = next((p for p in processes if p.pid == process_pid), None)
            
            if not target_process:
                self.logger.error(f"Process {process_pid} not found in container")
                # Try to find similar process
                netconf_processes = self.docker.find_netconf_processes_in_container(container_id)
                if netconf_processes:
                    target_process = netconf_processes[0]
                    process_pid = target_process.pid
                    self.logger.info(f"Using alternative process: PID {process_pid} ({target_process.name})")
                else:
                    return None
            
            # Step 3: Setup profiling
            container_output_file = f"/tmp/memory_analysis/{session_id}_{profiler_type}.xml"
            host_output_file = f"/tmp/{session_id}_{profiler_type}.xml"
            
            session = ContainerProfilingSession(
                session_id=session_id,
                container_id=container_id,
                container_name=container.name,
                process_pid=process_pid,
                process_name=target_process.name,
                profiler_type=profiler_type,
                output_file=host_output_file,
                container_output_file=container_output_file,
                start_time=datetime.now(),
                memory_increased=memory_increased,
                original_memory_limit=original_memory,
                new_memory_limit=memory_limit
            )
            
            # Step 4: Start profiling
            if profiler_type == "valgrind":
                success = self._start_valgrind_in_container(container_id, process_pid, container_output_file)
            else:
                success = self._start_asan_in_container(container_id, process_pid, container_output_file)
            
            if success:
                self.active_sessions[session_id] = session
                self.logger.info(f"Containerized profiling started successfully: {session_id}")
                return session
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to start containerized profiling: {e}")
            return None
    
    def stop_containerized_profiling(self, session_id: str) -> bool:
        """Stop containerized profiling session"""
        if session_id not in self.active_sessions:
            self.logger.error(f"Session {session_id} not found")
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            self.logger.info(f"Stopping containerized profiling session: {session_id}")
            
            # Step 1: Stop profiling process
            if session.profiler_type == "valgrind":
                self._stop_valgrind_in_container(session.container_id)
            
            # Step 2: Copy results from container to host
            self.logger.info("Copying profiling results from container...")
            copy_success = self.docker.copy_file_from_container(
                session.container_id,
                session.container_output_file,
                session.output_file
            )
            
            if not copy_success:
                self.logger.error("Failed to copy profiling results from container")
            
            # Step 3: Cleanup container files
            cleanup_cmd = f"rm -f {session.container_output_file} /tmp/memory_analysis/{session_id}*"
            self.docker.exec_into_container(session.container_id, cleanup_cmd)
            
            session.end_time = datetime.now()
            session.status = "completed" if copy_success else "failed"
            
            self.logger.info(f"Containerized profiling session {session_id} stopped")
            return copy_success
            
        except Exception as e:
            session.status = "failed"
            self.logger.error(f"Failed to stop session {session_id}: {e}")
            return False
    
    def download_session_logs(self, session_id: str, local_directory: Path) -> Optional[Path]:
        """Download profiling logs from device to local machine"""
        if session_id not in self.active_sessions:
            self.logger.error(f"Session {session_id} not found")
            return None
        
        session = self.active_sessions[session_id]
        local_directory.mkdir(parents=True, exist_ok=True)
        
        # Generate local filename
        local_filename = f"{session_id}_{session.profiler_type}.xml"
        local_path = local_directory / local_filename
        
        try:
            if self.device.download_file(session.output_file, local_path):
                self.logger.info(f"Downloaded containerized session logs to {local_path}")
                return local_path
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to download session logs: {e}")
            return None
    
    def get_container_diagnostics(self, container_id: str) -> Dict[str, Any]:
        """Get diagnostic information about container"""
        try:
            diagnostics = {}
            
            # Container status
            containers = self.docker.list_containers()
            container = next((c for c in containers if c.container_id.startswith(container_id)), None)
            if container:
                diagnostics['container_info'] = {
                    'name': container.name,
                    'status': container.status,
                    'memory_limit': container.memory_limit,
                    'memory_usage': container.memory_usage,
                    'cpu_usage': container.cpu_usage
                }
            
            # Container logs
            diagnostics['recent_logs'] = self.docker.get_container_logs(container_id, lines=20)
            
            # Processes
            processes = self.docker.get_container_processes(container_id)
            diagnostics['processes'] = [
                {
                    'pid': p.pid,
                    'name': p.name,
                    'command': p.command[:100],  # Truncate long commands
                    'memory_kb': p.memory_usage,
                    'cpu_percent': p.cpu_usage
                }
                for p in processes
            ]
            
            # Resource usage
            memory_info = self.docker._get_container_memory_info(container_id)
            diagnostics['resource_usage'] = memory_info
            
            return diagnostics
            
        except Exception as e:
            self.logger.error(f"Failed to get container diagnostics: {e}")
            return {}
    
    def restore_container_memory(self, session_id: str) -> bool:
        """Restore container to original memory settings"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        if not session.memory_increased:
            return True
        
        try:
            self.logger.info(f"Restoring container memory to original limit: {session.original_memory_limit}")
            
            container_config = ContainerConfig(
                container_id=session.container_id,
                memory_limit=session.original_memory_limit,
                restart_required=False  # No restart needed for memory update
            )
            
            return self.docker.increase_container_memory(
                session.container_id,
                session.original_memory_limit,
                container_config
            )
            
        except Exception as e:
            self.logger.error(f"Failed to restore container memory: {e}")
            return False
    
    def _start_valgrind_in_container(self, container_id: str, process_pid: int, output_file: str) -> bool:
        """Start Valgrind profiling inside container"""
        valgrind_options = [
            "--tool=memcheck",
            "--leak-check=full",
            "--show-leak-kinds=all",
            "--track-origins=yes",
            "--xml=yes",
            "--child-silent-after-fork=yes"
        ]
        
        return self.docker.start_valgrind_in_container(container_id, process_pid, output_file, valgrind_options)
    
    def _start_asan_in_container(self, container_id: str, process_pid: int, output_file: str) -> bool:
        """Start AddressSanitizer monitoring inside container"""
        # ASan should be pre-built into the application
        self.logger.info("AddressSanitizer should be pre-built into the application")
        
        # For ASan, we typically need to set environment variables and the application
        # should have been built with -fsanitize=address
        # Since it's already built-in, we just need to configure output
        try:
            # Set ASan environment variables in container
            asan_env_cmd = f"export ASAN_OPTIONS='log_path={output_file}:abort_on_error=1:fast_unwind_on_malloc=0'"
            exit_code, stdout, stderr = self.docker.exec_into_container(container_id, asan_env_cmd)
            
            if exit_code == 0:
                self.logger.info(f"AddressSanitizer configured for container {container_id}")
                return True
            else:
                self.logger.error(f"Failed to configure AddressSanitizer: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start AddressSanitizer in container: {e}")
            return False
    
    def _stop_valgrind_in_container(self, container_id: str):
        """Stop Valgrind process inside container"""
        try:
            # Find Valgrind process and stop it gracefully
            find_cmd = "ps aux | grep valgrind | grep -v grep | awk '{print $2}'"
            exit_code, stdout, stderr = self.docker.exec_into_container(container_id, find_cmd)
            
            if exit_code == 0 and stdout.strip():
                valgrind_pid = stdout.strip().split('\n')[0]
                kill_cmd = f"kill -TERM {valgrind_pid}"
                self.docker.exec_into_container(container_id, kill_cmd)
                time.sleep(5)  # Give Valgrind time to write final output
                
        except Exception as e:
            self.logger.error(f"Failed to stop Valgrind in container: {e}")
    
    def list_active_sessions(self) -> List[ContainerProfilingSession]:
        """List all active containerized profiling sessions"""
        return list(self.active_sessions.values()) 