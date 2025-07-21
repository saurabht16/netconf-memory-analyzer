"""
Device Connector for Memory Leak Analyzer
Handles SSH/Telnet connections to remote devices for memory analysis
"""

import paramiko
import socket
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import subprocess
import threading

@dataclass
class DeviceConfig:
    """Configuration for device connection"""
    hostname: str
    port: int = 22
    username: str = ""
    password: str = ""
    key_file: str = ""
    connection_type: str = "ssh"  # ssh, telnet
    timeout: int = 30
    working_dir: str = "/tmp"

@dataclass
class ProcessInfo:
    """Information about a running process"""
    pid: int
    name: str
    command: str
    memory_usage: int
    cpu_usage: float

class DeviceConnector:
    """Manages connections to remote devices for memory leak analysis"""
    
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.ssh_client = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
        
    def connect(self) -> bool:
        """Establish connection to the device"""
        try:
            if self.config.connection_type.lower() == "ssh":
                return self._connect_ssh()
            else:
                # Could add Telnet support here
                raise NotImplementedError("Telnet connection not implemented yet")
        except Exception as e:
            self.logger.error(f"Failed to connect to device: {e}")
            return False
    
    def _connect_ssh(self) -> bool:
        """Establish SSH connection"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connection parameters
            connect_params = {
                'hostname': self.config.hostname,
                'port': self.config.port,
                'username': self.config.username,
                'timeout': self.config.timeout
            }
            
            # Use key file or password
            if self.config.key_file:
                connect_params['key_filename'] = self.config.key_file
            else:
                connect_params['password'] = self.config.password
            
            self.ssh_client.connect(**connect_params)
            self.connected = True
            self.logger.info(f"Connected to device {self.config.hostname}")
            return True
            
        except Exception as e:
            self.logger.error(f"SSH connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close connection to device"""
        if self.ssh_client:
            self.ssh_client.close()
            self.connected = False
            self.logger.info("Disconnected from device")
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute command on remote device"""
        if not self.connected or not self.ssh_client:
            raise ConnectionError("Not connected to device")
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            # Wait for command completion
            exit_status = stdout.channel.recv_exit_status()
            
            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            return exit_status, stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise
    
    def find_netconf_processes(self) -> List[ProcessInfo]:
        """Find NETCONF-related processes on the device"""
        try:
            # Common NETCONF process names and patterns
            netconf_patterns = [
                "netconfd", "confd", "sshd_netconf", "netconf-server",
                "yang", "restconf", "gnmi"
            ]
            
            processes = []
            
            # Get process list
            exit_code, stdout, stderr = self.execute_command("ps aux")
            if exit_code != 0:
                self.logger.error(f"Failed to get process list: {stderr}")
                return processes
            
            for line in stdout.split('\n'):
                for pattern in netconf_patterns:
                    if pattern in line.lower() and 'ps aux' not in line:
                        # Parse ps output
                        fields = line.split()
                        if len(fields) >= 11:
                            try:
                                pid = int(fields[1])
                                cpu_usage = float(fields[2])
                                mem_usage = int(float(fields[3]) * 1024)  # Convert % to KB estimate
                                command = ' '.join(fields[10:])
                                
                                process_info = ProcessInfo(
                                    pid=pid,
                                    name=pattern,
                                    command=command,
                                    memory_usage=mem_usage,
                                    cpu_usage=cpu_usage
                                )
                                processes.append(process_info)
                                self.logger.info(f"Found NETCONF process: {pattern} (PID: {pid})")
                            except (ValueError, IndexError):
                                continue
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Error finding NETCONF processes: {e}")
            return []

    def kill_process(self, pid: int, signal: str = "TERM", use_sudo: bool = False) -> bool:
        """Kill a process by PID with optional signal and sudo"""
        try:
            # Prepare kill command
            kill_cmd = f"kill -{signal} {pid}"
            if use_sudo:
                kill_cmd = f"sudo {kill_cmd}"
            
            self.logger.info(f"Killing process PID {pid} with signal {signal}")
            exit_code, stdout, stderr = self.execute_command(kill_cmd)
            
            if exit_code == 0:
                self.logger.info(f"Successfully sent {signal} signal to process {pid}")
                
                # Wait a moment and verify process is gone
                time.sleep(2)
                if not self.is_process_running(pid):
                    self.logger.info(f"Process {pid} successfully terminated")
                    return True
                else:
                    self.logger.warning(f"Process {pid} still running after {signal} signal")
                    return False
            else:
                self.logger.error(f"Failed to kill process {pid}: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error killing process {pid}: {e}")
            return False

    def kill_process_by_name(self, process_name: str, signal: str = "TERM", use_sudo: bool = False) -> bool:
        """Kill processes by name using pkill"""
        try:
            # Prepare pkill command
            pkill_cmd = f"pkill -{signal} {process_name}"
            if use_sudo:
                pkill_cmd = f"sudo {pkill_cmd}"
            
            self.logger.info(f"Killing processes matching '{process_name}' with signal {signal}")
            exit_code, stdout, stderr = self.execute_command(pkill_cmd)
            
            if exit_code == 0:
                self.logger.info(f"Successfully sent {signal} signal to processes matching '{process_name}'")
                time.sleep(2)  # Wait for processes to terminate
                return True
            else:
                # pkill returns 1 if no processes found, which might be OK
                if "no processes found" in stderr.lower():
                    self.logger.info(f"No processes found matching '{process_name}'")
                    return True
                else:
                    self.logger.error(f"Failed to kill processes '{process_name}': {stderr}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Error killing processes by name '{process_name}': {e}")
            return False

    def is_process_running(self, pid: int) -> bool:
        """Check if a process is still running"""
        try:
            exit_code, stdout, stderr = self.execute_command(f"ps -p {pid}")
            return exit_code == 0 and str(pid) in stdout
        except Exception:
            return False

    def start_process_with_valgrind(self, 
                                  command: str, 
                                  valgrind_options: Dict[str, str] = None,
                                  working_dir: str = None,
                                  background: bool = True,
                                  use_sudo: bool = False) -> Tuple[bool, int]:
        """Start a process with Valgrind instrumentation"""
        try:
            # Default Valgrind options for memory leak detection
            default_valgrind_opts = {
                "tool": "memcheck",
                "leak-check": "full",
                "show-leak-kinds": "all",
                "track-origins": "yes",
                "verbose": "",
                "xml": "yes",
                "xml-file": "/tmp/valgrind_output_%p.xml",
                "gen-suppressions": "all"
            }
            
            # Merge with user options
            if valgrind_options:
                default_valgrind_opts.update(valgrind_options)
            
            # Build Valgrind command
            valgrind_cmd_parts = ["valgrind"]
            for option, value in default_valgrind_opts.items():
                if value == "":
                    valgrind_cmd_parts.append(f"--{option}")
                else:
                    valgrind_cmd_parts.append(f"--{option}={value}")
            
            # Add the actual command
            valgrind_cmd_parts.append(command)
            valgrind_cmd = " ".join(valgrind_cmd_parts)
            
            # Add sudo if needed
            if use_sudo:
                valgrind_cmd = f"sudo {valgrind_cmd}"
            
            # Change directory if specified
            if working_dir:
                valgrind_cmd = f"cd {working_dir} && {valgrind_cmd}"
            
            # Run in background if requested
            if background:
                valgrind_cmd = f"nohup {valgrind_cmd} > /dev/null 2>&1 &"
            
            self.logger.info(f"Starting process with Valgrind: {valgrind_cmd}")
            exit_code, stdout, stderr = self.execute_command(valgrind_cmd, timeout=60)
            
            if exit_code == 0:
                # Try to find the new process PID
                time.sleep(2)  # Wait for process to start
                
                # Extract process name from command for PID lookup
                process_name = command.split()[0].split('/')[-1]
                processes = self.find_process_by_name(process_name)
                
                if processes:
                    new_pid = processes[0].pid
                    self.logger.info(f"Successfully started process with Valgrind, PID: {new_pid}")
                    return True, new_pid
                else:
                    self.logger.warning("Process started but PID not found")
                    return True, -1
            else:
                self.logger.error(f"Failed to start process with Valgrind: {stderr}")
                return False, -1
                
        except Exception as e:
            self.logger.error(f"Error starting process with Valgrind: {e}")
            return False, -1

    def find_process_by_name(self, process_name: str) -> List[ProcessInfo]:
        """Find processes by name"""
        try:
            processes = []
            exit_code, stdout, stderr = self.execute_command(f"pgrep -f {process_name}")
            
            if exit_code == 0:
                pids = [int(pid.strip()) for pid in stdout.split('\n') if pid.strip()]
                
                for pid in pids:
                    # Get detailed info for each PID
                    exit_code, ps_output, _ = self.execute_command(f"ps -p {pid} -o pid,pcpu,pmem,cmd --no-headers")
                    if exit_code == 0 and ps_output.strip():
                        fields = ps_output.strip().split(None, 3)
                        if len(fields) >= 4:
                            process_info = ProcessInfo(
                                pid=int(fields[0]),
                                name=process_name,
                                command=fields[3],
                                memory_usage=int(float(fields[2]) * 1024),  # Convert % to KB estimate
                                cpu_usage=float(fields[1])
                            )
                            processes.append(process_info)
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Error finding process by name '{process_name}': {e}")
            return []

    def restart_process_with_valgrind(self, 
                                    process_name: str,
                                    start_command: str,
                                    valgrind_options: Dict[str, str] = None,
                                    kill_signal: str = "TERM",
                                    use_sudo: bool = False,
                                    wait_time: int = 5) -> Tuple[bool, int]:
        """Kill existing process and restart it with Valgrind"""
        try:
            self.logger.info(f"Restarting process '{process_name}' with Valgrind instrumentation")
            
            # Step 1: Find and kill existing processes
            existing_processes = self.find_process_by_name(process_name)
            if existing_processes:
                self.logger.info(f"Found {len(existing_processes)} existing processes to terminate")
                
                # Kill all existing processes
                for process in existing_processes:
                    if not self.kill_process(process.pid, kill_signal, use_sudo):
                        self.logger.warning(f"Failed to kill process PID {process.pid}")
                
                # If TERM didn't work, try KILL
                time.sleep(wait_time)
                remaining_processes = self.find_process_by_name(process_name)
                if remaining_processes:
                    self.logger.warning(f"Some processes still running, using KILL signal")
                    for process in remaining_processes:
                        self.kill_process(process.pid, "KILL", use_sudo)
                    time.sleep(2)
            else:
                self.logger.info(f"No existing processes found for '{process_name}'")
            
            # Step 2: Wait for cleanup
            time.sleep(wait_time)
            
            # Step 3: Start new process with Valgrind
            success, new_pid = self.start_process_with_valgrind(
                command=start_command,
                valgrind_options=valgrind_options,
                use_sudo=use_sudo
            )
            
            if success:
                self.logger.info(f"Successfully restarted '{process_name}' with Valgrind, PID: {new_pid}")
                return True, new_pid
            else:
                self.logger.error(f"Failed to restart '{process_name}' with Valgrind")
                return False, -1
                
        except Exception as e:
            self.logger.error(f"Error restarting process with Valgrind: {e}")
            return False, -1

    def stop_valgrind_process(self, pid: int, output_file: str = None) -> bool:
        """Stop a Valgrind-instrumented process and collect results"""
        try:
            self.logger.info(f"Stopping Valgrind process PID {pid}")
            
            # Send TERM signal first for clean shutdown
            if self.kill_process(pid, "TERM"):
                self.logger.info(f"Valgrind process {pid} terminated cleanly")
                
                # Wait for Valgrind to write output
                time.sleep(5)
                
                # Check if output file exists
                if output_file:
                    exit_code, stdout, stderr = self.execute_command(f"ls -la {output_file}")
                    if exit_code == 0:
                        self.logger.info(f"Valgrind output file created: {output_file}")
                    else:
                        self.logger.warning(f"Valgrind output file not found: {output_file}")
                
                return True
            else:
                self.logger.error(f"Failed to stop Valgrind process {pid}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping Valgrind process: {e}")
            return False
    
    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """Upload file to remote device"""
        if not self.connected or not self.ssh_client:
            raise ConnectionError("Not connected to device")
        
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.put(str(local_path), remote_path)
            sftp.close()
            self.logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            self.logger.error(f"File upload failed: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """Download file from remote device"""
        if not self.connected or not self.ssh_client:
            raise ConnectionError("Not connected to device")
        
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.get(remote_path, str(local_path))
            sftp.close()
            self.logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            self.logger.error(f"File download failed: {e}")
            return False
    
    def create_remote_directory(self, path: str) -> bool:
        """Create directory on remote device"""
        try:
            exit_code, stdout, stderr = self.execute_command(f"mkdir -p {path}")
            return exit_code == 0
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, str]:
        """Get system information from the device"""
        info = {}
        
        commands = {
            'hostname': 'hostname',
            'uptime': 'uptime',
            'memory': 'free -h',
            'disk': 'df -h',
            'os_version': 'cat /etc/os-release | head -5',
            'kernel': 'uname -a'
        }
        
        for key, command in commands.items():
            try:
                exit_code, stdout, stderr = self.execute_command(command, timeout=10)
                if exit_code == 0:
                    info[key] = stdout.strip()
                else:
                    info[key] = f"Command failed: {stderr}"
            except Exception as e:
                info[key] = f"Error: {e}"
        
        return info
    
    def __enter__(self):
        """Context manager entry"""
        if not self.connect():
            raise ConnectionError("Failed to connect to device")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect() 