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
                "sysrepo", "libnetconf", "netopeer", "yanglint"
            ]
            
            processes = []
            
            # Use ps command to find processes
            ps_command = "ps aux | grep -E '(" + "|".join(netconf_patterns) + ")' | grep -v grep"
            exit_code, stdout, stderr = self.execute_command(ps_command)
            
            if exit_code == 0:
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split(None, 10)
                        if len(parts) >= 11:
                            try:
                                processes.append(ProcessInfo(
                                    pid=int(parts[1]),
                                    name=parts[10].split()[0],
                                    command=parts[10],
                                    memory_usage=int(parts[5]) if parts[5].isdigit() else 0,
                                    cpu_usage=float(parts[2]) if parts[2].replace('.', '').isdigit() else 0.0
                                ))
                            except (ValueError, IndexError):
                                continue
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Failed to find NETCONF processes: {e}")
            return []
    
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