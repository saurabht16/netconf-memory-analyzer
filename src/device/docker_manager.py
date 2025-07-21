"""
Docker Container Manager for Memory Leak Testing
Handles Docker container operations, memory allocation, and containerized process profiling
"""

import time
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from .device_connector import DeviceConnector, ProcessInfo

@dataclass
class ContainerInfo:
    """Information about a Docker container"""
    container_id: str
    name: str
    image: str
    status: str
    memory_limit: str
    memory_usage: str
    cpu_usage: str
    ports: List[str]
    created: str

@dataclass
class ContainerConfig:
    """Configuration for container operations"""
    container_name: str = ""
    container_id: str = ""
    memory_limit: str = "5g"  # Default 5GB
    restart_required: bool = True
    backup_before_modify: bool = True
    timeout_seconds: int = 300

class DockerManager:
    """Manages Docker containers for memory leak testing"""
    
    def __init__(self, device_connector: DeviceConnector):
        self.device = device_connector
        self.logger = logging.getLogger(__name__)
        
    def list_containers(self, show_all: bool = True) -> List[ContainerInfo]:
        """List all Docker containers on the device"""
        try:
            # Get container information using docker ps
            cmd_filter = "-a" if show_all else ""
            docker_cmd = f"docker ps {cmd_filter} --format 'table {{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}\\t{{{{.CreatedAt}}}}'"
            
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd)
            
            if exit_code != 0:
                self.logger.error(f"Failed to list containers: {stderr}")
                return []
            
            containers = []
            lines = stdout.strip().split('\n')
            
            # Skip header line
            for line in lines[1:]:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        # Get memory usage for this container
                        memory_info = self._get_container_memory_info(parts[0])
                        
                        containers.append(ContainerInfo(
                            container_id=parts[0],
                            name=parts[1],
                            image=parts[2],
                            status=parts[3],
                            memory_limit=memory_info.get('limit', 'unknown'),
                            memory_usage=memory_info.get('usage', 'unknown'),
                            cpu_usage=memory_info.get('cpu', 'unknown'),
                            ports=parts[4].split(',') if parts[4] else [],
                            created=parts[5]
                        ))
            
            return containers
            
        except Exception as e:
            self.logger.error(f"Failed to list containers: {e}")
            return []
    
    def find_netconf_containers(self) -> List[ContainerInfo]:
        """Find containers that likely contain NETCONF applications"""
        containers = self.list_containers()
        netconf_containers = []
        
        # Common NETCONF container patterns
        netconf_patterns = [
            'netconf', 'confd', 'sysrepo', 'yanglint', 'netopeer',
            'ui', 'frontend', 'backend', 'api', 'server'
        ]
        
        for container in containers:
            # Check container name and image for NETCONF patterns
            container_text = f"{container.name} {container.image}".lower()
            
            for pattern in netconf_patterns:
                if pattern in container_text:
                    netconf_containers.append(container)
                    break
        
        return netconf_containers
    
    def get_container_processes(self, container_id: str) -> List[ProcessInfo]:
        """Get processes running inside a specific container"""
        try:
            # Use docker exec to run ps inside the container
            ps_cmd = f"docker exec {container_id} ps aux"
            exit_code, stdout, stderr = self.device.execute_command(ps_cmd)
            
            if exit_code != 0:
                self.logger.error(f"Failed to get container processes: {stderr}")
                return []
            
            processes = []
            lines = stdout.strip().split('\n')
            
            # Skip header line
            for line in lines[1:]:
                if line.strip():
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        try:
                            processes.append(ProcessInfo(
                                pid=int(parts[1]),
                                name=parts[10].split()[0] if parts[10] else parts[0],
                                command=parts[10] if parts[10] else '',
                                memory_usage=int(parts[5]) if parts[5].isdigit() else 0,
                                cpu_usage=float(parts[2]) if parts[2].replace('.', '').isdigit() else 0.0
                            ))
                        except (ValueError, IndexError):
                            continue
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Failed to get container processes: {e}")
            return []
    
    def find_netconf_processes_in_container(self, container_id: str) -> List[ProcessInfo]:
        """Find NETCONF processes within a specific container"""
        processes = self.get_container_processes(container_id)
        
        # Common NETCONF process patterns
        netconf_patterns = [
            'netconfd', 'confd', 'sshd_netconf', 'netconf-server',
            'sysrepo', 'libnetconf', 'netopeer', 'yanglint',
            'node', 'python', 'java', 'nginx'  # Common for UI containers
        ]
        
        netconf_processes = []
        for process in processes:
            process_text = f"{process.name} {process.command}".lower()
            
            for pattern in netconf_patterns:
                if pattern in process_text:
                    netconf_processes.append(process)
                    break
        
        return netconf_processes
    
    def increase_container_memory(self, container_id: str, memory_limit: str, config: ContainerConfig) -> bool:
        """Increase container memory allocation without restarting"""
        try:
            self.logger.info(f"Increasing memory for container {container_id} to {memory_limit}")
            
            # Get current container configuration
            current_config = self._get_container_config(container_id)
            
            if config.backup_before_modify:
                self._backup_container_config(container_id, current_config)
            
            # Update container memory limit without stopping
            self.logger.info(f"Updating container memory limit to {memory_limit} (no restart required)...")
            update_cmd = f"docker update --memory={memory_limit} --memory-swap={memory_limit} {container_id}"
            exit_code, stdout, stderr = self.device.execute_command(update_cmd)
            
            if exit_code != 0:
                self.logger.error(f"Failed to update container memory: {stderr}")
                return False
            
            # Verify memory update
            new_memory_info = self._get_container_memory_info(container_id)
            self.logger.info(f"Container memory updated. New limit: {new_memory_info.get('limit', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to increase container memory: {e}")
            return False
    
    def exec_into_container(self, container_id: str, command: str, interactive: bool = False) -> Tuple[int, str, str]:
        """Execute command inside a container"""
        try:
            # Build docker exec command
            exec_flags = "-it" if interactive else ""
            docker_exec_cmd = f"docker exec {exec_flags} {container_id} {command}"
            
            return self.device.execute_command(docker_exec_cmd)
            
        except Exception as e:
            self.logger.error(f"Failed to exec into container: {e}")
            return 1, "", str(e)
    
    def start_valgrind_in_container(self, container_id: str, process_pid: int, output_file: str, valgrind_options: List[str]) -> bool:
        """Start Valgrind profiling on a process inside a container"""
        try:
            # Valgrind is already available in the container build - no installation needed
            self.logger.info("Starting Valgrind profiling (using pre-built Valgrind)...")
            
            # Create output directory inside container
            output_dir = str(Path(output_file).parent)
            self.exec_into_container(container_id, f"mkdir -p {output_dir}")
            
            # Build Valgrind command
            options_str = " ".join(valgrind_options)
            valgrind_cmd = f"valgrind {options_str} --xml-file={output_file} --pid={process_pid}"
            
            # Run Valgrind in background inside container
            bg_cmd = f"nohup {valgrind_cmd} > /dev/null 2>&1 &"
            exit_code, stdout, stderr = self.exec_into_container(container_id, bg_cmd)
            
            if exit_code == 0:
                self.logger.info(f"Valgrind started in container {container_id} for PID {process_pid}")
                return True
            else:
                self.logger.error(f"Failed to start Valgrind: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start Valgrind in container: {e}")
            return False
    
    def copy_file_from_container(self, container_id: str, container_path: str, host_path: str) -> bool:
        """Copy file from container to host"""
        try:
            copy_cmd = f"docker cp {container_id}:{container_path} {host_path}"
            exit_code, stdout, stderr = self.device.execute_command(copy_cmd)
            
            if exit_code == 0:
                self.logger.info(f"File copied from container: {container_path} -> {host_path}")
                return True
            else:
                self.logger.error(f"Failed to copy file from container: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to copy file from container: {e}")
            return False
    
    def _get_container_memory_info(self, container_id: str) -> Dict[str, str]:
        """Get memory information for a container"""
        try:
            stats_cmd = f"docker stats {container_id} --no-stream --format 'table {{{{.MemUsage}}}}\\t{{{{.MemPerc}}}}\\t{{{{.CPUPerc}}}}'"
            exit_code, stdout, stderr = self.device.execute_command(stats_cmd)
            
            if exit_code == 0 and stdout.strip():
                lines = stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    parts = lines[1].split('\t')
                    if len(parts) >= 3:
                        return {
                            'usage': parts[0],
                            'limit': parts[0].split('/')[-1].strip() if '/' in parts[0] else 'unknown',
                            'memory_percent': parts[1],
                            'cpu': parts[2]
                        }
            
            return {'usage': 'unknown', 'limit': 'unknown', 'cpu': 'unknown'}
            
        except Exception:
            return {'usage': 'unknown', 'limit': 'unknown', 'cpu': 'unknown'}
    
    def _get_container_config(self, container_id: str) -> Dict[str, Any]:
        """Get current container configuration"""
        try:
            inspect_cmd = f"docker inspect {container_id}"
            exit_code, stdout, stderr = self.device.execute_command(inspect_cmd)
            
            if exit_code == 0:
                return json.loads(stdout)[0]
            else:
                return {}
                
        except Exception:
            return {}
    
    def _backup_container_config(self, container_id: str, config: Dict[str, Any]):
        """Backup container configuration"""
        try:
            backup_file = f"/tmp/container_backup_{container_id}_{int(time.time())}.json"
            backup_cmd = f"echo '{json.dumps(config)}' > {backup_file}"
            self.device.execute_command(backup_cmd)
            self.logger.info(f"Container config backed up to {backup_file}")
        except Exception as e:
            self.logger.warning(f"Failed to backup container config: {e}")
    
    def _wait_for_container_ready(self, container_id: str, timeout_seconds: int):
        """Wait for container to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if container is running
                status_cmd = f"docker inspect {container_id} --format '{{{{.State.Status}}}}'"
                exit_code, stdout, stderr = self.device.execute_command(status_cmd)
                
                if exit_code == 0 and stdout.strip() == "running":
                    # Container is running, wait a bit more for services to start
                    time.sleep(10)
                    self.logger.info("Container is ready")
                    return
                    
                time.sleep(5)
                
            except Exception:
                time.sleep(5)
        
        self.logger.warning(f"Container may not be fully ready after {timeout_seconds} seconds")
    
    def get_container_logs(self, container_id: str, lines: int = 50) -> str:
        """Get recent logs from container"""
        try:
            logs_cmd = f"docker logs --tail {lines} {container_id}"
            exit_code, stdout, stderr = self.device.execute_command(logs_cmd)
            
            if exit_code == 0:
                return stdout
            else:
                return stderr
                
        except Exception as e:
            return f"Failed to get logs: {e}" 