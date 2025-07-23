"""
Configurable Container Setup Manager
Handles flexible container preparation with custom commands and file editing
"""

import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .device_connector import DeviceConnector

@dataclass
class FileEdit:
    """Configuration for editing a file inside container"""
    file: str
    content: str
    backup: bool = True
    backup_suffix: str = ".backup"
    permissions: Optional[str] = None

@dataclass
class ContainerSetupConfig:
    """Configuration for container setup sequence"""
    pre_commands: List[str]
    file_edits: List[FileEdit]
    valgrind_command: str
    post_commands: List[str]
    cleanup_commands: List[str]

class ConfigurableContainerSetup:
    """Manages configurable container setup with custom commands and file editing"""
    
    def __init__(self, device_connector: DeviceConnector):
        self.device = device_connector
        self.logger = logging.getLogger(__name__)
        self.template_vars = {}
    
    def set_template_variables(self, **kwargs):
        """Set template variables for command substitution"""
        self.template_vars.update(kwargs)
        # Add timestamp if not provided
        if 'timestamp' not in self.template_vars:
            self.template_vars['timestamp'] = int(time.time())
    
    def _substitute_template(self, text: str) -> str:
        """Substitute template variables in text"""
        result = text
        for key, value in self.template_vars.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def execute_container_setup(self, container_id: str, setup_config: ContainerSetupConfig) -> bool:
        """Execute the complete container setup sequence"""
        try:
            self.logger.info(f"🔧 Starting configurable container setup for {container_id}")
            
            # Set container_id in template vars
            self.set_template_variables(container_id=container_id)
            
            # Step 1: Execute pre-commands
            if setup_config.pre_commands:
                if not self._execute_pre_commands(container_id, setup_config.pre_commands):
                    return False
            
            # Step 2: Edit files
            if setup_config.file_edits:
                if not self._edit_files(container_id, setup_config.file_edits):
                    return False
            
            # Step 3: Start Valgrind with custom command
            if not self._start_valgrind_with_config(container_id, setup_config.valgrind_command):
                return False
            
            # Step 4: Execute post-commands
            if setup_config.post_commands:
                if not self._execute_post_commands(container_id, setup_config.post_commands):
                    self.logger.warning("Post-commands failed, but Valgrind is running")
            
            self.logger.info(f"✅ Container setup completed for {container_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Container setup failed for {container_id}: {e}")
            return False
    
    def _execute_pre_commands(self, container_id: str, pre_commands: List[str]) -> bool:
        """Execute pre-setup commands"""
        self.logger.info(f"🚀 Executing {len(pre_commands)} pre-commands...")
        
        for i, command in enumerate(pre_commands, 1):
            try:
                # Substitute template variables
                final_command = self._substitute_template(command)
                
                self.logger.info(f"   [{i}/{len(pre_commands)}] {final_command}")
                
                # Execute command in container
                docker_cmd = f"sudo docker exec {container_id} sh -c '{final_command}'"
                exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=60)
                
                if exit_code == 0:
                    self.logger.info(f"      ✅ Command {i} completed successfully")
                    if stdout.strip():
                        self.logger.debug(f"      Output: {stdout.strip()}")
                else:
                    self.logger.error(f"      ❌ Command {i} failed: {stderr}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error executing pre-command {i}: {e}")
                return False
        
        return True
    
    def _edit_files(self, container_id: str, file_edits: List[FileEdit]) -> bool:
        """Edit files inside the container"""
        self.logger.info(f"📝 Editing {len(file_edits)} files...")
        
        for i, file_edit in enumerate(file_edits, 1):
            try:
                file_path = self._substitute_template(file_edit.file)
                file_content = self._substitute_template(file_edit.content)
                
                self.logger.info(f"   [{i}/{len(file_edits)}] Editing {file_path}")
                
                # Create backup if requested
                if file_edit.backup:
                    backup_path = f"{file_path}{file_edit.backup_suffix}"
                    backup_cmd = f"sudo docker exec {container_id} cp {file_path} {backup_path} 2>/dev/null || true"
                    self.device.execute_command(backup_cmd, timeout=10)
                    self.logger.debug(f"      📋 Backup created: {backup_path}")
                
                # Create temporary file with content
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file_path = tmp_file.name
                
                try:
                    # Copy content to container
                    copy_cmd = f"sudo docker cp {tmp_file_path} {container_id}:{file_path}"
                    exit_code, stdout, stderr = self.device.execute_command(copy_cmd, timeout=30)
                    
                    if exit_code == 0:
                        self.logger.info(f"      ✅ File {file_path} updated successfully")
                        
                        # Set permissions if specified
                        if file_edit.permissions:
                            perm_cmd = f"sudo docker exec {container_id} chmod {file_edit.permissions} {file_path}"
                            self.device.execute_command(perm_cmd, timeout=10)
                            self.logger.debug(f"      🔒 Permissions set to {file_edit.permissions}")
                    else:
                        self.logger.error(f"      ❌ Failed to update {file_path}: {stderr}")
                        return False
                        
                finally:
                    # Clean up temporary file
                    Path(tmp_file_path).unlink(missing_ok=True)
                    
            except Exception as e:
                self.logger.error(f"Error editing file {i}: {e}")
                return False
        
        return True
    
    def _start_valgrind_with_config(self, container_id: str, valgrind_command: str) -> bool:
        """Start Valgrind with custom configuration"""
        try:
            # Substitute template variables
            final_valgrind_cmd = self._substitute_template(valgrind_command)
            
            self.logger.info(f"🚀 Starting Valgrind with custom command...")
            self.logger.info(f"   Command: {final_valgrind_cmd}")
            
            # Execute Valgrind command in container
            docker_cmd = f"sudo docker exec -d {container_id} sh -c '{final_valgrind_cmd}'"
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=30)
            
            if exit_code == 0:
                self.logger.info("✅ Valgrind started successfully with custom configuration")
                
                # Wait a moment and verify it's running
                time.sleep(3)
                check_cmd = f"sudo docker exec {container_id} ps aux | grep valgrind | grep -v grep"
                exit_code, stdout, stderr = self.device.execute_command(check_cmd, timeout=10)
                
                if exit_code == 0 and stdout.strip():
                    self.logger.info("✅ Valgrind process verified running")
                    return True
                else:
                    self.logger.warning("⚠️ Valgrind may not be running (verification failed)")
                    return True  # Still return True as command executed successfully
            else:
                self.logger.error(f"❌ Failed to start Valgrind: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Valgrind: {e}")
            return False
    
    def _execute_post_commands(self, container_id: str, post_commands: List[str]) -> bool:
        """Execute post-setup commands"""
        self.logger.info(f"📋 Executing {len(post_commands)} post-commands...")
        
        for i, command in enumerate(post_commands, 1):
            try:
                # Substitute template variables
                final_command = self._substitute_template(command)
                
                self.logger.info(f"   [{i}/{len(post_commands)}] {final_command}")
                
                # Execute command in container
                docker_cmd = f"sudo docker exec {container_id} sh -c '{final_command}'"
                exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=30)
                
                if exit_code == 0:
                    self.logger.info(f"      ✅ Post-command {i} completed")
                    if stdout.strip():
                        self.logger.debug(f"      Output: {stdout.strip()}")
                else:
                    self.logger.warning(f"      ⚠️ Post-command {i} failed: {stderr}")
                    # Continue with other commands even if one fails
                    
            except Exception as e:
                self.logger.warning(f"Error executing post-command {i}: {e}")
                # Continue with other commands
        
        return True
    
    def execute_cleanup_commands(self, container_id: str, cleanup_commands: List[str]) -> bool:
        """Execute cleanup commands when stopping"""
        if not cleanup_commands:
            return True
            
        self.logger.info(f"🧹 Executing {len(cleanup_commands)} cleanup commands...")
        
        for i, command in enumerate(cleanup_commands, 1):
            try:
                # Substitute template variables
                final_command = self._substitute_template(command)
                
                self.logger.info(f"   [{i}/{len(cleanup_commands)}] {final_command}")
                
                # Execute command in container
                docker_cmd = f"sudo docker exec {container_id} sh -c '{final_command}'"
                exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=30)
                
                if exit_code == 0:
                    self.logger.info(f"      ✅ Cleanup command {i} completed")
                else:
                    self.logger.warning(f"      ⚠️ Cleanup command {i} failed: {stderr}")
                    # Continue with other cleanup commands
                    
            except Exception as e:
                self.logger.warning(f"Error executing cleanup command {i}: {e}")
                # Continue with other commands
        
        return True
    
    @staticmethod
    def parse_container_setup_config(config_dict: Dict[str, Any]) -> ContainerSetupConfig:
        """Parse container setup configuration from dictionary"""
        
        # Parse file edits
        file_edits = []
        for file_edit_dict in config_dict.get('file_edits', []):
            file_edit = FileEdit(
                file=file_edit_dict['file'],
                content=file_edit_dict['content'],
                backup=file_edit_dict.get('backup', True),
                backup_suffix=file_edit_dict.get('backup_suffix', '.backup'),
                permissions=file_edit_dict.get('permissions')
            )
            file_edits.append(file_edit)
        
        return ContainerSetupConfig(
            pre_commands=config_dict.get('pre_commands', []),
            file_edits=file_edits,
            valgrind_command=config_dict.get('valgrind_command', ''),
            post_commands=config_dict.get('post_commands', []),
            cleanup_commands=config_dict.get('cleanup_commands', [])
        ) 