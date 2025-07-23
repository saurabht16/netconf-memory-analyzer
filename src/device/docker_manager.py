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
        
    def find_target_netconf_container(self, preferred_patterns: List[str] = None) -> Optional[ContainerInfo]:
        """Find the target NETCONF container efficiently - stops on first match"""
        try:
            self.logger.info("🔍 Searching for target NETCONF container...")
            
            # Default patterns ordered by preference (UI containers first, then NETCONF)
            if preferred_patterns is None:
                preferred_patterns = [
                    'ui', 'frontend', 'netconf-ui', 'web-ui',
                    'netconf', 'netconfd', 'confd', 'sysrepo', 
                    'backend', 'api', 'server', 'yanglint', 'netopeer'
                ]
            
            # Search for containers using targeted docker commands
            for pattern in preferred_patterns:
                self.logger.debug(f"   Searching for pattern: {pattern}")
                
                # Use docker ps with name filter for efficiency
                docker_cmd = f"sudo docker ps --filter name={pattern} --format '{{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}\\t{{{{.CreatedAt}}}}'"
                exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=10)
                
                if exit_code == 0 and stdout.strip():
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) >= 4:
                                container_id = parts[0]
                                container_name = parts[1]
                                
                                self.logger.info(f"🎯 Found target container: {container_name} ({container_id[:12]})")
                                
                                # Get memory info only for this container
                                memory_info = self._get_container_memory_info(container_id)
                                
                                container_info = ContainerInfo(
                                    container_id=container_id,
                                    name=container_name,
                                    image=parts[2],
                                    status=parts[3],
                                    memory_limit=memory_info.get('limit', 'unknown'),
                                    memory_usage=memory_info.get('usage', 'unknown'),
                                    cpu_usage=memory_info.get('cpu', 'unknown'),
                                    ports=parts[4].split(',') if len(parts) > 4 and parts[4] else [],
                                    created=parts[5] if len(parts) > 5 else 'unknown'
                                )
                                
                                # Verify it has NETCONF processes before returning
                                if self._verify_netconf_container(container_id):
                                    self.logger.info(f"✅ Confirmed NETCONF container: {container_name}")
                                    return container_info
                                else:
                                    self.logger.debug(f"   Container {container_name} has no NETCONF processes, continuing search...")
            
            # Fallback: search by image patterns
            self.logger.info("   Trying image-based search...")
            image_patterns = ['netconf', 'confd', 'sysrepo', 'ui']
            
            for pattern in image_patterns:
                docker_cmd = f"sudo docker ps --filter ancestor={pattern} --format '{{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}'"
                exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=10)
                
                if exit_code == 0 and stdout.strip():
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) >= 4:
                                container_id = parts[0]
                                container_name = parts[1]
                                
                                self.logger.info(f"🎯 Found container by image: {container_name} ({container_id[:12]})")
                                
                                if self._verify_netconf_container(container_id):
                                    memory_info = self._get_container_memory_info(container_id)
                                    
                                    container_info = ContainerInfo(
                                        container_id=container_id,
                                        name=container_name,
                                        image=parts[2],
                                        status=parts[3],
                                        memory_limit=memory_info.get('limit', 'unknown'),
                                        memory_usage=memory_info.get('usage', 'unknown'),
                                        cpu_usage=memory_info.get('cpu', 'unknown'),
                                        ports=[],
                                        created='unknown'
                                    )
                                    
                                    self.logger.info(f"✅ Confirmed NETCONF container: {container_name}")
                                    return container_info
            
            self.logger.warning("❌ No target NETCONF container found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding target NETCONF container: {e}")
            return None
    
    def _verify_netconf_container(self, container_id: str) -> bool:
        """Quick verification that container has NETCONF processes"""
        try:
            # Quick check for NETCONF processes without full parsing
            ps_cmd = f"sudo docker exec {container_id} ps aux | grep -E 'netconf|confd' | grep -v grep"
            exit_code, stdout, stderr = self.device.execute_command(ps_cmd, timeout=5)
            
            has_netconf = exit_code == 0 and stdout.strip()
            self.logger.debug(f"   Container {container_id[:12]} NETCONF verification: {'✅' if has_netconf else '❌'}")
            return has_netconf
            
        except Exception:
            return False
    
    def get_target_container_details(self, container_id: str) -> Optional[ContainerInfo]:
        """Get detailed information for a specific container only"""
        try:
            self.logger.info(f"📊 Getting details for container {container_id[:12]}")
            
            # Get basic container info
            inspect_cmd = f"sudo docker inspect {container_id} --format '{{{{.Name}}}}|{{{{.Config.Image}}}}|{{{{.State.Status}}}}|{{{{.Created}}}}'"
            exit_code, stdout, stderr = self.device.execute_command(inspect_cmd, timeout=10)
            
            if exit_code != 0:
                self.logger.error(f"Failed to inspect container: {stderr}")
                return None
            
            parts = stdout.strip().split('|')
            if len(parts) < 4:
                return None
            
            container_name = parts[0].lstrip('/')  # Remove leading slash
            image = parts[1]
            status = parts[2]
            created = parts[3]
            
            # Get memory info
            memory_info = self._get_container_memory_info(container_id)
            
            # Get port mappings
            ports_cmd = f"sudo docker port {container_id}"
            exit_code, port_output, _ = self.device.execute_command(ports_cmd, timeout=5)
            ports = port_output.strip().split('\n') if exit_code == 0 and port_output.strip() else []
            
            container_info = ContainerInfo(
                container_id=container_id,
                name=container_name,
                image=image,
                status=status,
                memory_limit=memory_info.get('limit', 'unknown'),
                memory_usage=memory_info.get('usage', 'unknown'),
                cpu_usage=memory_info.get('cpu', 'unknown'),
                ports=ports,
                created=created
            )
            
            self.logger.info(f"✅ Container details: {container_name} | Status: {status} | Memory: {memory_info.get('usage', '?')}/{memory_info.get('limit', '?')}")
            return container_info
            
        except Exception as e:
            self.logger.error(f"Error getting container details: {e}")
            return None

    # Keep original methods for backward compatibility but mark as deprecated
    def list_containers(self, show_all: bool = True) -> List[ContainerInfo]:
        """List all Docker containers on the device - DEPRECATED: Use find_target_netconf_container() for efficiency"""
        self.logger.warning("⚠️ list_containers() is deprecated for efficiency. Use find_target_netconf_container() instead.")
        try:
            # Get container information using docker ps
            cmd_filter = "-a" if show_all else ""
            docker_cmd = f"sudo docker ps {cmd_filter} --format 'table {{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}\\t{{{{.CreatedAt}}}}'"
            
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
        """Find containers that likely contain NETCONF applications - DEPRECATED: Use find_target_netconf_container() for efficiency"""
        self.logger.warning("⚠️ find_netconf_containers() is deprecated for efficiency. Use find_target_netconf_container() instead.")
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
            ps_cmd = f"sudo docker exec {container_id} ps aux"
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
        """Find all NETCONF-related processes in a container"""
        try:
            self.logger.info(f"🔍 Finding NETCONF processes in container {container_id}")
            
            # Enhanced NETCONF process patterns - be more comprehensive
            netconf_patterns = [
                "netconfd", "netconf-server", "confd", "sshd_netconf", 
                "ietf-netconf", "yang-netconf", "restconf", "gnmi",
                "sysrepod", "sysrepo", "netopeer2", "yanglint"
            ]
            
            # Get all processes in container with sudo
            ps_cmd = f"sudo docker exec {container_id} ps aux"
            exit_code, stdout, stderr = self.device.execute_command(ps_cmd, timeout=15)
            
            if exit_code != 0:
                self.logger.error(f"Failed to get process list from container: {stderr}")
                return []
            
            netconf_processes = []
            lines = stdout.strip().split('\n')
            
            # Skip header line
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                # Check if any NETCONF pattern matches - be more aggressive
                line_lower = line.lower()
                found_pattern = None
                for pattern in netconf_patterns:
                    if pattern in line_lower and 'ps aux' not in line_lower:
                        found_pattern = pattern
                        break
                
                if found_pattern:
                    # Parse ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                    fields = line.split()
                    if len(fields) >= 11:
                        try:
                            pid = int(fields[1])
                            cpu_usage = float(fields[2])
                            mem_percent = float(fields[3])
                            command = ' '.join(fields[10:])
                            
                            # Estimate memory usage (rough calculation)
                            memory_usage = int(mem_percent * 1024)  # Convert % to KB estimate
                            
                            process_info = ProcessInfo(
                                pid=pid,
                                name=found_pattern,
                                command=command,
                                memory_usage=memory_usage,
                                cpu_usage=cpu_usage
                            )
                            netconf_processes.append(process_info)
                            self.logger.info(f"📋 Found NETCONF process: {found_pattern} (PID: {pid}) - {command}")
                        except (ValueError, IndexError) as e:
                            self.logger.debug(f"Failed to parse process line: {line} - {e}")
                            continue
            
            # Also try to find processes by command name directly
            self.logger.info("🔍 Double-checking with pgrep...")
            for pattern in ["netconfd", "confd"]:
                pgrep_cmd = f"sudo docker exec {container_id} pgrep -f {pattern}"
                exit_code, stdout, stderr = self.device.execute_command(pgrep_cmd, timeout=10)
                
                if exit_code == 0 and stdout.strip():
                    pids = [int(pid.strip()) for pid in stdout.split('\n') if pid.strip().isdigit()]
                    for pid in pids:
                        # Check if we already have this PID
                        if not any(p.pid == pid for p in netconf_processes):
                            # Get process details
                            ps_detail_cmd = f"sudo docker exec {container_id} ps -p {pid} -o pid,pcpu,pmem,cmd --no-headers"
                            exit_code, ps_output, _ = self.device.execute_command(ps_detail_cmd, timeout=5)
                            if exit_code == 0 and ps_output.strip():
                                fields = ps_output.strip().split(None, 3)
                                if len(fields) >= 4:
                                    process_info = ProcessInfo(
                                        pid=pid,
                                        name=pattern,
                                        command=fields[3],
                                        memory_usage=int(float(fields[2]) * 1024),
                                        cpu_usage=float(fields[1])
                                    )
                                    netconf_processes.append(process_info)
                                    self.logger.info(f"📋 Additional NETCONF process: {pattern} (PID: {pid}) - {fields[3]}")
            
            self.logger.info(f"🎯 Found {len(netconf_processes)} total NETCONF processes in container {container_id}")
            return netconf_processes
            
        except Exception as e:
            self.logger.error(f"Error finding NETCONF processes in container: {e}")
            return []

    def kill_netconf_processes_in_container(self, container_id: str, signal: str = "TERM") -> bool:
        """Kill ALL NETCONF processes in a container - comprehensive approach"""
        try:
            self.logger.info(f"🛑 Killing ALL NETCONF processes in container {container_id}")
            
            # Method 1: Find and kill by PID
            netconf_processes = self.find_netconf_processes_in_container(container_id)
            
            if not netconf_processes:
                self.logger.info(f"No NETCONF processes found in container {container_id}")
            else:
                self.logger.info(f"🛑 Killing {len(netconf_processes)} NETCONF processes by PID")
                
                # Kill each process
                for process in netconf_processes:
                    self.logger.info(f"Killing process PID {process.pid} ({process.name}): {process.command}")
                    
                    kill_cmd = f"sudo docker exec {container_id} kill -{signal} {process.pid}"
                    exit_code, stdout, stderr = self.device.execute_command(kill_cmd, timeout=10)
                    
                    if exit_code == 0:
                        self.logger.info(f"✅ Successfully sent {signal} signal to PID {process.pid}")
                    else:
                        self.logger.warning(f"⚠️ Failed to kill PID {process.pid}: {stderr}")
            
            # Method 2: Kill by process name patterns - more comprehensive
            self.logger.info("🛑 Killing processes by name patterns...")
            kill_patterns = ["netconfd", "confd", "netconf-server"]
            
            for pattern in kill_patterns:
                # Try pkill first
                pkill_cmd = f"sudo docker exec {container_id} pkill -{signal} -f {pattern}"
                exit_code, stdout, stderr = self.device.execute_command(pkill_cmd, timeout=10)
                
                if exit_code == 0:
                    self.logger.info(f"✅ pkill successful for pattern: {pattern}")
                elif "no process found" not in stderr.lower():
                    self.logger.debug(f"pkill for {pattern}: {stderr}")
                
                # Also try killall as backup
                killall_cmd = f"sudo docker exec {container_id} killall -{signal} {pattern} 2>/dev/null || true"
                self.device.execute_command(killall_cmd, timeout=5)
            
            # Wait for processes to terminate
            self.logger.info("⏱️ Waiting for processes to terminate...")
            time.sleep(5)
            
            # Method 3: Check if any processes are still running and force kill
            remaining_processes = self.find_netconf_processes_in_container(container_id)
            if remaining_processes and signal == "TERM":
                self.logger.warning(f"⚠️ {len(remaining_processes)} processes still running, using KILL signal")
                
                # Force kill remaining processes
                for process in remaining_processes:
                    kill_cmd = f"sudo docker exec {container_id} kill -KILL {process.pid}"
                    exit_code, stdout, stderr = self.device.execute_command(kill_cmd, timeout=5)
                    if exit_code == 0:
                        self.logger.info(f"🔪 Force killed PID {process.pid}")
                
                # Also force kill by name
                for pattern in kill_patterns:
                    force_kill_cmd = f"sudo docker exec {container_id} pkill -KILL -f {pattern} 2>/dev/null || true"
                    self.device.execute_command(force_kill_cmd, timeout=5)
                
                time.sleep(3)
                final_check = self.find_netconf_processes_in_container(container_id)
                if final_check:
                    self.logger.error(f"❌ {len(final_check)} processes still running after KILL signal:")
                    for proc in final_check:
                        self.logger.error(f"   PID {proc.pid}: {proc.command}")
                    return False
            
            self.logger.info(f"✅ Successfully killed all NETCONF processes in container {container_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error killing NETCONF processes in container: {e}")
            return False

    def start_netconfd_with_valgrind_in_container(self, 
                                                container_id: str,
                                                netconfd_command: str = "/usr/bin/netconfd --foreground",
                                                valgrind_options: Dict[str, str] = None,
                                                working_dir: str = None) -> Tuple[bool, int]:
        """Start netconfd with Valgrind in container - kills ALL existing processes first"""
        try:
            self.logger.info(f"🎯 Starting netconfd with Valgrind in container {container_id}")
            
            # Step 1: Kill ALL existing NETCONF processes aggressively
            self.logger.info("🛑 Step 1: Aggressively killing ALL existing NETCONF processes...")
            
            # Multiple attempts to ensure clean slate
            for attempt in range(3):
                self.logger.info(f"   Attempt {attempt + 1}/3 to kill processes...")
                
                if not self.kill_netconf_processes_in_container(container_id, "TERM"):
                    self.logger.warning(f"   Attempt {attempt + 1} - Some processes might still be running")
                
                # Wait and check
                time.sleep(2)
                remaining = self.find_netconf_processes_in_container(container_id)
                if not remaining:
                    self.logger.info("   ✅ All NETCONF processes successfully killed")
                    break
                else:
                    self.logger.warning(f"   ⚠️ {len(remaining)} processes still running")
                    if attempt == 2:  # Last attempt
                        self.logger.error("   ❌ Failed to kill all processes after 3 attempts")
                        return False, -1
            
            # Step 2: Verify Valgrind is available
            self.logger.info("🔍 Step 2: Verifying Valgrind availability...")
            valgrind_check_cmd = f"sudo docker exec {container_id} which valgrind"
            exit_code, stdout, stderr = self.device.execute_command(valgrind_check_cmd, timeout=10)
            
            if exit_code != 0:
                self.logger.error("❌ Valgrind not available in container")
                return False, -1
            
            valgrind_path = stdout.strip()
            self.logger.info(f"✅ Valgrind found at: {valgrind_path}")
            
            # Step 3: Prepare Valgrind command properly
            self.logger.info("⚙️ Step 3: Preparing Valgrind command...")
            default_valgrind_opts = {
                "tool": "memcheck",
                "leak-check": "full",
                "show-leak-kinds": "all", 
                "track-origins": "yes",
                "xml": "yes",
                "xml-file": "/tmp/valgrind_netconfd_%p.xml",
                "gen-suppressions": "all",
                "child-silent-after-fork": "yes",
                "trace-children": "yes",
                "verbose": ""
            }
            
            if valgrind_options:
                default_valgrind_opts.update(valgrind_options)
            
            # Build Valgrind command parts
            valgrind_cmd_parts = [valgrind_path]
            for option, value in default_valgrind_opts.items():
                if value == "":
                    valgrind_cmd_parts.append(f"--{option}")
                else:
                    valgrind_cmd_parts.append(f"--{option}={value}")
            
            # IMPORTANT: Add the netconfd command AFTER all Valgrind options
            valgrind_cmd_parts.append(netconfd_command)
            valgrind_cmd = " ".join(valgrind_cmd_parts)
            
            self.logger.info(f"🔧 Valgrind command: {valgrind_cmd}")
            
            # Step 4: Start netconfd with Valgrind in background
            self.logger.info(f"🚀 Step 4: Starting netconfd with Valgrind...")
            
            # Construct full docker command with sudo
            if working_dir:
                docker_cmd = f"sudo docker exec -d -w {working_dir} {container_id} sh -c '{valgrind_cmd}'"
            else:
                docker_cmd = f"sudo docker exec -d {container_id} sh -c '{valgrind_cmd}'"
            
            self.logger.info(f"🐳 Docker command: {docker_cmd}")
            
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=30)
            
            if exit_code == 0:
                self.logger.info("✅ Valgrind + netconfd started successfully")
                
                # Step 5: Find the new process PID
                self.logger.info("🔍 Step 5: Finding new Valgrind process PID...")
                time.sleep(5)  # Wait for process to start
                
                # Look for Valgrind process with sudo
                ps_cmd = f"sudo docker exec {container_id} ps aux | grep valgrind | grep -v grep"
                exit_code, stdout, stderr = self.device.execute_command(ps_cmd, timeout=10)
                
                if exit_code == 0 and stdout.strip():
                    # Parse the PID from ps output
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        fields = line.split()
                        if len(fields) >= 2 and 'netconfd' in line:
                            try:
                                valgrind_pid = int(fields[1])
                                self.logger.info(f"🎯 Found Valgrind+netconfd process PID: {valgrind_pid}")
                                return True, valgrind_pid
                            except ValueError:
                                continue
                
                # Fallback: look for any netconfd process
                self.logger.info("🔍 Fallback: Looking for netconfd process...")
                netconf_processes = self.find_netconf_processes_in_container(container_id)
                if netconf_processes:
                    new_pid = netconf_processes[0].pid
                    self.logger.info(f"🎯 Found netconfd process PID: {new_pid}")
                    return True, new_pid
                else:
                    self.logger.warning("⚠️ Process started but PID not found")
                    return True, -1
            else:
                self.logger.error(f"❌ Failed to start Valgrind + netconfd: {stderr}")
                return False, -1
                
        except Exception as e:
            self.logger.error(f"Error starting netconfd with Valgrind: {e}")
            return False, -1

    def restart_netconfd_normally_in_container(self, container_id: str, 
                                             netconfd_command: str = "/usr/bin/netconfd --foreground") -> bool:
        """Stop Valgrind+netconfd and restart netconfd normally"""
        try:
            self.logger.info(f"🔄 Restarting netconfd normally in container {container_id}")
            
            # Kill all existing processes (including Valgrind)
            self.logger.info("🛑 Killing all existing NETCONF and Valgrind processes...")
            
            # Kill Valgrind processes specifically
            valgrind_kill_cmd = f"sudo docker exec {container_id} pkill -KILL -f valgrind || true"
            self.device.execute_command(valgrind_kill_cmd, timeout=10)
            
            # Kill all NETCONF processes
            self.kill_netconf_processes_in_container(container_id, "KILL")
            
            # Wait for cleanup
            time.sleep(3)
            
            # Start netconfd normally in background
            self.logger.info("🚀 Starting netconfd normally...")
            normal_start_cmd = f"sudo docker exec -d {container_id} {netconfd_command}"
            exit_code, stdout, stderr = self.device.execute_command(normal_start_cmd, timeout=15)
            
            if exit_code == 0:
                self.logger.info("✅ netconfd restarted normally")
                return True
            else:
                self.logger.error(f"❌ Failed to restart netconfd: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restarting netconfd normally: {e}")
            return False

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
            update_cmd = f"sudo docker update --memory={memory_limit} --memory-swap={memory_limit} {container_id}"
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
            docker_exec_cmd = f"sudo docker exec {exec_flags} {container_id} {command}"
            
            return self.device.execute_command(docker_exec_cmd)
            
        except Exception as e:
            self.logger.error(f"Error executing command in container: {e}")
            return 1, "", str(e)
    
    def start_valgrind_in_container(self, container_id: str, target_pid: int, 
                                  output_file: str = "/tmp/valgrind_output.xml",
                                  valgrind_options: Dict[str, str] = None) -> bool:
        """Start Valgrind profiling in container"""
        try:
            # Check if Valgrind is available
            if not self.verify_valgrind_in_container(container_id):
                return False
            
            # Default Valgrind options
            default_opts = {
                "tool": "memcheck",
                "leak-check": "full",
                "show-leak-kinds": "all",
                "track-origins": "yes",
                "xml": "yes",
                "xml-file": output_file
            }
            
            if valgrind_options:
                default_opts.update(valgrind_options)
            
            # Build Valgrind command for attaching to process
            valgrind_cmd_parts = ["valgrind"]
            for option, value in default_opts.items():
                if value == "":
                    valgrind_cmd_parts.append(f"--{option}")
                else:
                    valgrind_cmd_parts.append(f"--{option}={value}")
            
            valgrind_cmd_parts.append(f"--pid={target_pid}")
            valgrind_cmd = " ".join(valgrind_cmd_parts)
            
            # Execute in container
            docker_cmd = f"sudo docker exec -d {container_id} {valgrind_cmd}"
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd)
            
            if exit_code == 0:
                self.logger.info(f"Valgrind started in container {container_id} for PID {target_pid}")
                return True
            else:
                self.logger.error(f"Failed to start Valgrind in container: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Valgrind in container: {e}")
            return False

    def kill_process_in_container(self, container_id: str, pid: int, signal: str = "TERM") -> bool:
        """Kill a process inside a container"""
        try:
            self.logger.info(f"Killing process PID {pid} in container {container_id} with signal {signal}")
            
            # Use docker exec to kill process
            kill_cmd = f"sudo docker exec {container_id} kill -{signal} {pid}"
            exit_code, stdout, stderr = self.device.execute_command(kill_cmd)
            
            if exit_code == 0:
                self.logger.info(f"Successfully sent {signal} signal to process {pid}")
                time.sleep(2)  # Wait for process termination
                
                # Verify process is gone
                if not self.is_process_running_in_container(container_id, pid):
                    self.logger.info(f"Process {pid} successfully terminated in container")
                    return True
                else:
                    self.logger.warning(f"Process {pid} still running after {signal} signal")
                    return False
            else:
                self.logger.error(f"Failed to kill process {pid} in container: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error killing process in container: {e}")
            return False

    def is_process_running_in_container(self, container_id: str, pid: int) -> bool:
        """Check if a process is running inside a container"""
        try:
            ps_cmd = f"sudo docker exec {container_id} ps -p {pid}"
            exit_code, stdout, stderr = self.device.execute_command(ps_cmd)
            return exit_code == 0 and str(pid) in stdout
        except Exception:
            return False

    def start_process_with_valgrind_in_container(self, 
                                               container_id: str,
                                               command: str,
                                               valgrind_options: Dict[str, str] = None,
                                               working_dir: str = None,
                                               background: bool = True) -> Tuple[bool, int]:
        """Start a new process with Valgrind inside a container"""
        try:
            # Default Valgrind options
            default_valgrind_opts = {
                "tool": "memcheck",
                "leak-check": "full",
                "show-leak-kinds": "all",
                "track-origins": "yes",
                "xml": "yes",
                "xml-file": "/tmp/valgrind_output_%p.xml",
                "verbose": ""
            }
            
            if valgrind_options:
                default_valgrind_opts.update(valgrind_options)
            
            # Build Valgrind command
            valgrind_cmd_parts = ["valgrind"]
            for option, value in default_valgrind_opts.items():
                if value == "":
                    valgrind_cmd_parts.append(f"--{option}")
                else:
                    valgrind_cmd_parts.append(f"--{option}={value}")
            
            valgrind_cmd_parts.append(command)
            valgrind_cmd = " ".join(valgrind_cmd_parts)
            
            # Prepare docker exec command
            docker_exec_flags = "-d" if background else "-it"
            if working_dir:
                docker_cmd = f"sudo docker exec {docker_exec_flags} -w {working_dir} {container_id} {valgrind_cmd}"
            else:
                docker_cmd = f"sudo docker exec {docker_exec_flags} {container_id} {valgrind_cmd}"
            
            self.logger.info(f"Starting process with Valgrind in container: {docker_cmd}")
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=60)
            
            if exit_code == 0:
                # Find the new process PID
                time.sleep(2)
                process_name = command.split()[0].split('/')[-1]
                processes = self.get_container_processes(container_id)
                
                for process in processes:
                    if process_name in process.command:
                        self.logger.info(f"Process started with Valgrind in container, PID: {process.pid}")
                        return True, process.pid
                
                self.logger.warning("Process started but PID not found")
                return True, -1
            else:
                self.logger.error(f"Failed to start process with Valgrind in container: {stderr}")
                return False, -1
                
        except Exception as e:
            self.logger.error(f"Error starting process with Valgrind in container: {e}")
            return False, -1

    def restart_netconf_with_valgrind_in_container(self, 
                                                 container_id: str,
                                                 netconf_command: str = None,
                                                 valgrind_options: Dict[str, str] = None,
                                                 wait_time: int = 5) -> Tuple[bool, int]:
        """Kill existing NETCONF process and restart with Valgrind in container"""
        try:
            self.logger.info(f"Restarting NETCONF with Valgrind in container {container_id}")
            
            # Step 1: Find NETCONF processes in container
            netconf_processes = []
            all_processes = self.get_container_processes(container_id)
            
            for process in all_processes:
                if any(name in process.command.lower() for name in ['netconfd', 'confd', 'netconf']):
                    netconf_processes.append(process)
            
            # Step 2: Kill existing NETCONF processes
            if netconf_processes:
                self.logger.info(f"Found {len(netconf_processes)} NETCONF processes to terminate")
                for process in netconf_processes:
                    if netconf_command is None:
                        # Use the existing command for restart
                        netconf_command = process.command
                    
                    if not self.kill_process_in_container(container_id, process.pid, "TERM"):
                        # Try KILL if TERM doesn't work
                        time.sleep(2)
                        self.kill_process_in_container(container_id, process.pid, "KILL")
            else:
                self.logger.info("No existing NETCONF processes found in container")
                if netconf_command is None:
                    netconf_command = "/usr/bin/netconfd --foreground"
            
            # Step 3: Wait for cleanup
            time.sleep(wait_time)
            
            # Step 4: Start NETCONF with Valgrind
            success, new_pid = self.start_process_with_valgrind_in_container(
                container_id=container_id,
                command=netconf_command,
                valgrind_options=valgrind_options,
                background=True
            )
            
            if success:
                self.logger.info(f"Successfully restarted NETCONF with Valgrind in container, PID: {new_pid}")
                return True, new_pid
            else:
                self.logger.error("Failed to restart NETCONF with Valgrind in container")
                return False, -1
                
        except Exception as e:
            self.logger.error(f"Error restarting NETCONF with Valgrind in container: {e}")
            return False, -1

    def collect_valgrind_output_from_container(self, container_id: str, 
                                             internal_path: str = "/tmp/valgrind_output.xml",
                                             local_path: str = None) -> str:
        """Copy Valgrind output file from container to local system"""
        try:
            if local_path is None:
                local_path = f"valgrind_output_{container_id}.xml"
            
            # Copy file from container
            copy_cmd = f"docker cp {container_id}:{internal_path} {local_path}"
            exit_code, stdout, stderr = self.device.execute_command(copy_cmd)
            
            if exit_code == 0:
                self.logger.info(f"Valgrind output copied from container to {local_path}")
                return local_path
            else:
                self.logger.error(f"Failed to copy Valgrind output from container: {stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error collecting Valgrind output from container: {e}")
            return None
    
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
            inspect_cmd = f"sudo docker inspect {container_id}"
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
                status_cmd = f"sudo docker inspect {container_id} --format '{{{{.State.Status}}}}'"
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

    def start_netconfd_with_configurable_setup(self, 
                                              container_id: str,
                                              container_setup_config: Dict[str, Any],
                                              template_vars: Dict[str, Any] = None) -> Tuple[bool, int]:
        """Start netconfd using configurable container setup"""
        try:
            from .configurable_container_setup import ConfigurableContainerSetup, ContainerSetupConfig
            
            self.logger.info(f"🔧 Starting configurable container setup for {container_id}")
            
            # Parse container setup configuration
            if 'container_setup' in container_setup_config:
                setup_dict = container_setup_config['container_setup']
            else:
                # Fallback to default if no container_setup specified
                setup_dict = {
                    'pre_commands': [],
                    'file_edits': [],
                    'valgrind_command': 'valgrind --tool=memcheck --leak-check=full --xml=yes --xml-file=/tmp/valgrind_%p.xml /usr/bin/netconfd --foreground',
                    'post_commands': [],
                    'cleanup_commands': []
                }
            
            setup_config = ConfigurableContainerSetup.parse_container_setup_config(setup_dict)
            
            # Create configurable setup manager
            configurable_setup = ConfigurableContainerSetup(self.device)
            
            # Set template variables
            if template_vars:
                configurable_setup.set_template_variables(**template_vars)
            
            # Kill existing NETCONF processes first
            self.logger.info("🛑 Killing existing NETCONF processes...")
            self.kill_netconf_processes_in_container(container_id, "TERM")
            
            # Execute configurable setup
            success = configurable_setup.execute_container_setup(container_id, setup_config)
            
            if success:
                # Try to find the Valgrind process PID
                time.sleep(3)
                ps_cmd = f"sudo docker exec {container_id} ps aux | grep valgrind | grep -v grep"
                exit_code, stdout, stderr = self.device.execute_command(ps_cmd, timeout=10)
                
                valgrind_pid = -1
                if exit_code == 0 and stdout.strip():
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        fields = line.split()
                        if len(fields) >= 2 and 'netconfd' in line:
                            try:
                                valgrind_pid = int(fields[1])
                                break
                            except ValueError:
                                continue
                
                self.logger.info(f"✅ Configurable container setup completed, Valgrind PID: {valgrind_pid}")
                return True, valgrind_pid
            else:
                self.logger.error("❌ Configurable container setup failed")
                return False, -1
                
        except ImportError:
            self.logger.error("❌ ConfigurableContainerSetup not available")
            return False, -1
        except Exception as e:
            self.logger.error(f"❌ Error in configurable container setup: {e}")
            return False, -1
    
    def cleanup_configurable_container(self, 
                                     container_id: str, 
                                     cleanup_commands: List[str],
                                     template_vars: Dict[str, Any] = None) -> bool:
        """Execute cleanup commands from configurable setup"""
        try:
            from .configurable_container_setup import ConfigurableContainerSetup
            
            if not cleanup_commands:
                return True
            
            self.logger.info(f"🧹 Running configurable cleanup for {container_id}")
            
            # Create configurable setup manager
            configurable_setup = ConfigurableContainerSetup(self.device)
            
            # Set template variables
            if template_vars:
                configurable_setup.set_template_variables(**template_vars)
            
            # Execute cleanup commands
            success = configurable_setup.execute_cleanup_commands(container_id, cleanup_commands)
            
            if success:
                self.logger.info("✅ Configurable cleanup completed")
            else:
                self.logger.warning("⚠️ Some cleanup commands failed")
            
            return success
            
        except ImportError:
            self.logger.warning("ConfigurableContainerSetup not available for cleanup")
            return True
        except Exception as e:
            self.logger.error(f"Error in configurable cleanup: {e}")
            return False 