"""
Device Connector for Memory Leak Analyzer
Handles SSH connections to remote devices with network device support
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
    use_diag_shell: bool = True  # Enter diagnostic shell for Docker access
    use_sudo_docker: bool = True  # Use sudo for Docker commands
    diag_command: str = "diag shell host"  # Command to enter diagnostic shell

@dataclass
class ProcessInfo:
    """Information about a running process"""
    pid: int
    name: str
    command: str
    memory_usage: int
    cpu_usage: float

class DeviceConnector:
    """Manages SSH connections to remote devices for memory leak analysis"""
    
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.ssh_client = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.in_diag_shell = False
        self.docker_accessible = False
        
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
            
            # Automatically set up diagnostic shell if needed
            if self.config.use_diag_shell:
                if self._setup_diag_shell():
                    self.logger.info("Successfully configured diagnostic shell for Docker access")
                else:
                    self.logger.warning("Failed to configure diagnostic shell, Docker commands may fail")
            else:
                # Test Docker access without diag shell
                self._test_docker_access()
            
            return True
            
        except Exception as e:
            self.logger.error(f"SSH connection failed: {e}")
            return False
    
    def _setup_diag_shell(self) -> bool:
        """Set up diagnostic shell for Docker access"""
        try:
            # First test if Docker is already accessible
            if self._test_docker_access():
                self.logger.info("Docker already accessible, no diagnostic shell needed")
                return True
            
            # Try to enter diagnostic shell
            self.logger.info(f"Entering diagnostic shell with command: {self.config.diag_command}")
            exit_code, stdout, stderr = self._execute_raw_command(self.config.diag_command, timeout=15)
            
            if exit_code == 0:
                self.in_diag_shell = True
                self.logger.info("Successfully entered diagnostic shell")
                
                # Test Docker access again
                if self._test_docker_access():
                    self.logger.info("Docker now accessible via diagnostic shell")
                    return True
                else:
                    self.logger.warning("Entered diagnostic shell but Docker still not accessible")
                    return False
            else:
                self.logger.warning(f"Failed to enter diagnostic shell: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting up diagnostic shell: {e}")
            return False
    
    def _test_docker_access(self) -> bool:
        """Test if Docker is accessible (with or without sudo)"""
        # Test without sudo first
        exit_code, stdout, stderr = self._execute_raw_command("docker --version", timeout=10)
        if exit_code == 0 and "Docker version" in stdout:
            self.docker_accessible = True
            self.logger.debug("Docker accessible without sudo")
            return True
        
        # Test with sudo if configured
        if self.config.use_sudo_docker:
            exit_code, stdout, stderr = self._execute_raw_command("sudo docker --version", timeout=10)
            if exit_code == 0 and "Docker version" in stdout:
                self.docker_accessible = True
                self.logger.debug("Docker accessible with sudo")
                return True
        
        self.docker_accessible = False
        self.logger.debug("Docker not accessible")
        return False
    
    def _execute_raw_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute raw command without any modifications"""
        if not self.connected or not self.ssh_client:
            raise ConnectionError("Not connected to device")
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            return exit_status, stdout_data, stderr_data
        except Exception as e:
            self.logger.error(f"Raw command execution failed: {e}")
            return 1, "", str(e)
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute command on remote device with automatic Docker handling"""
        if not self.connected or not self.ssh_client:
            raise ConnectionError("Not connected to device")
        
        try:
            # Prepare command with appropriate context
            final_command = self._prepare_command(command)
            
            stdin, stdout, stderr = self.ssh_client.exec_command(final_command, timeout=timeout)
            
            # Wait for command completion
            exit_status = stdout.channel.recv_exit_status()
            
            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            return exit_status, stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise
    
    def _prepare_command(self, command: str) -> str:
        """Prepare command with diagnostic shell and sudo as needed"""
        original_command = command.strip()
        
        # Check if this is a Docker command
        is_docker_command = (
            original_command.startswith('docker ') or
            'docker exec' in original_command or
            'docker ps' in original_command or
            'docker inspect' in original_command
        )
        
        if not is_docker_command:
            # Non-Docker command, return as-is
            return original_command
        
        # This is a Docker command, apply transformations
        prepared_command = original_command
        
        # Add sudo if needed
        if self.config.use_sudo_docker and not prepared_command.startswith('sudo '):
            prepared_command = f"sudo {prepared_command}"
            self.logger.debug(f"Added sudo to Docker command: {prepared_command}")
        
        # Wrap with diagnostic shell if needed and not already in it
        if self.config.use_diag_shell and not self.in_diag_shell:
            prepared_command = f"{self.config.diag_command} -c '{prepared_command}'"
            self.logger.debug(f"Wrapped with diagnostic shell: {prepared_command}")
        
        self.logger.debug(f"Command transformation: '{original_command}' -> '{prepared_command}'")
        return prepared_command
    
    def disconnect(self):
        """Close connection to device"""
        if self.ssh_client:
            self.ssh_client.close()
            self.connected = False
            self.logger.info("Disconnected from device")
    
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