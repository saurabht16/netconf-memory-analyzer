#!/usr/bin/env python3
"""
Configurable Container Setup
Handles custom container preparation with environment-preserving single-session execution
"""

import logging
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .device_connector import DeviceConnector

@dataclass
class FileEdit:
    """File editing configuration"""
    file: str
    content: str
    backup: bool = False
    permissions: Optional[str] = None

@dataclass
class ContainerSetupConfig:
    """Container setup configuration"""
    pre_commands: List[str] = None
    file_edits: List[FileEdit] = None
    valgrind_command: str = ""
    post_commands: List[str] = None
    cleanup_commands: List[str] = None
    working_dir: Optional[str] = None
    use_single_session: bool = True  # NEW: Enable single session by default

class ConfigurableContainerSetup:
    """Configurable container setup with custom commands and file editing"""
    
    def __init__(self, device_connector):
        self.device = device_connector
        self.logger = logging.getLogger(__name__)
        self.template_vars = {}
    
    def set_template_variables(self, variables: Dict[str, str]):
        """Set template variables for command substitution"""
        self.template_vars = variables
    
    def execute_container_setup(self, container_id: str, config: ContainerSetupConfig) -> bool:
        """Execute container setup using single session bash script"""
        
        try:
            self.logger.info(f"🔧 Starting configurable container setup for {container_id}")
            
            # Check if we should use single session mode (recommended)
            if getattr(config, 'use_single_session', True):
                return self._execute_single_session_setup(container_id, config)
            else:
                # Fallback to original multi-session approach
                return self._execute_multi_session_setup(container_id, config)
                
        except Exception as e:
            self.logger.error(f"Container setup failed: {e}")
            return False
    
    def _execute_single_session_setup(self, container_id: str, config: ContainerSetupConfig) -> bool:
        """Execute all commands in a single bash session to preserve environment variables"""
        
        # Build list of all commands
        all_commands = []
        
        # Add pre-commands
        if config.pre_commands:
            self.logger.info(f"📋 Adding {len(config.pre_commands)} pre-commands")
            all_commands.extend(config.pre_commands)
        
        # Add Valgrind command if specified
        if config.valgrind_command:
            self.logger.info("🚀 Adding Valgrind command")
            # Add background execution for Valgrind
            valgrind_cmd = config.valgrind_command
            if not valgrind_cmd.endswith('&'):
                valgrind_cmd += ' &'
            all_commands.append(valgrind_cmd)
            all_commands.append('sleep 3')  # Wait for Valgrind to start
            all_commands.append('ps aux | grep valgrind | grep -v grep || echo "Valgrind not found"')  # Verify
        
        # Add post-commands
        if config.post_commands:
            self.logger.info(f"📋 Adding {len(config.post_commands)} post-commands")
            all_commands.extend(config.post_commands)
        
        # Handle file edits separately (they need docker cp)
        if config.file_edits:
            self.logger.info("📝 Processing file edits...")
            for file_edit in config.file_edits:
                if not self._edit_file(container_id, file_edit):
                    return False
        
        # Execute all commands in single session if we have any
        if all_commands:
            return self._execute_commands_as_script(container_id, all_commands, config.working_dir)
        else:
            self.logger.info("✅ No commands to execute")
            return True
    
    def _execute_commands_as_script(self, container_id: str, commands: List[str], working_dir: Optional[str] = None) -> bool:
        """Generate and execute a bash script from command list"""
        
        try:
            # Generate bash script content
            script_content = self._generate_bash_script(commands, working_dir)
            
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp_file:
                tmp_file.write(script_content)
                tmp_script_path = tmp_file.name
            
            try:
                # Copy script to container
                copy_cmd = f"sudo docker cp {tmp_script_path} {container_id}:/tmp/setup_script.sh"
                exit_code, stdout, stderr = self.device.execute_command(copy_cmd, timeout=30)
                
                if exit_code != 0:
                    self.logger.error(f"Failed to copy script to container: {stderr}")
                    return False
                
                # Execute script in container (single session preserves environment)
                exec_cmd = f"sudo docker exec {container_id} bash -c 'chmod +x /tmp/setup_script.sh && /tmp/setup_script.sh'"
                
                self.logger.info(f"🚀 Executing {len(commands)} commands in single container session...")
                
                # Execute with extended timeout
                total_timeout = len(commands) * 30 + 120  # 30s per command + 2min buffer
                exit_code, stdout, stderr = self.device.execute_command(exec_cmd, timeout=total_timeout)
                
                # Log the output
                if stdout:
                    self.logger.info("📋 Script output:")
                    for line in stdout.split('\n'):
                        if line.strip():
                            self.logger.info(f"   {line}")
                
                if exit_code == 0:
                    self.logger.info("✅ Single session script execution completed successfully")
                else:
                    self.logger.error(f"❌ Script execution failed: {stderr}")
                
                # Clean up script from container
                cleanup_cmd = f"sudo docker exec {container_id} rm -f /tmp/setup_script.sh"
                self.device.execute_command(cleanup_cmd, timeout=10)
                
                return exit_code == 0
                
            finally:
                # Clean up local temporary file
                Path(tmp_script_path).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"Error executing commands as script: {e}")
            return False
    
    def _generate_bash_script(self, commands: List[str], working_dir: Optional[str] = None) -> str:
        """Generate bash script content from command list"""
        
        script_lines = [
            "#!/bin/bash",
            "set -e  # Exit on any error",
            "",
            "echo '=== Starting Single Session Container Setup ==='",
            "echo 'Session PID: $$'",
            "echo 'Environment variables will persist across all commands'",
            ""
        ]
        
        # Add working directory change if specified
        if working_dir:
            script_lines.append(f"cd {working_dir}")
            script_lines.append(f"echo 'Changed to working directory: {working_dir}'")
            script_lines.append("")
        
        # Add each command with logging
        for i, command in enumerate(commands):
            # Substitute template variables
            final_command = self._substitute_template(command)
            
            script_lines.extend([
                f"# Command {i+1}",
                f"echo '--- Executing Command {i+1}: {final_command[:50]}{'...' if len(final_command) > 50 else ''} ---'",
                final_command,
                "echo '✅ Command completed'",
                ""
            ])
        
        script_lines.append("echo '=== Single Session Setup Complete ==='")
        
        return "\n".join(script_lines)
    
    def _edit_file(self, container_id: str, file_edit: FileEdit) -> bool:
        """Edit a single file"""
        
        try:
            # Substitute template variables in content
            file_content = self._substitute_template(file_edit.content)
            file_path = self._substitute_template(file_edit.file)
            
            self.logger.info(f"      📝 Editing {file_path}")
            
            # Create backup if requested
            if file_edit.backup:
                backup_cmd = f"sudo docker exec {container_id} cp {file_path} {file_path}.backup_{int(time.time())}"
                exit_code, stdout, stderr = self.device.execute_command(backup_cmd, timeout=10)
                if exit_code == 0:
                    self.logger.debug(f"      💾 Backup created for {file_path}")
            
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
                    
                    return True
                else:
                    self.logger.error(f"      ❌ Failed to update {file_path}: {stderr}")
                    return False
                    
            finally:
                # Clean up temporary file
                Path(tmp_file_path).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"Error editing file {file_edit.file}: {e}")
            return False
    
    def _substitute_template(self, text: str) -> str:
        """Substitute template variables in text"""
        result = text
        for key, value in self.template_vars.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def _execute_multi_session_setup(self, container_id: str, config: ContainerSetupConfig) -> bool:
        """Execute setup using multiple sessions (original approach)"""
        
        self.logger.warning("⚠️ Using multi-session mode - environment variables won't persist between commands")
        
        # Execute pre-commands
        if config.pre_commands and not self._execute_pre_commands(container_id, config.pre_commands):
            return False
        
        # Edit files
        if config.file_edits and not self._edit_files(container_id, config.file_edits):
            return False
        
        # Start Valgrind
        if config.valgrind_command and not self._start_valgrind_with_config(container_id, config.valgrind_command):
            return False
        
        # Execute post-commands
        if config.post_commands and not self._execute_post_commands(container_id, config.post_commands):
            return False
        
        return True

    # Keep existing methods for backward compatibility
    def _execute_pre_commands(self, container_id: str, pre_commands: List[str]) -> bool:
        """Execute pre-setup commands"""
        self.logger.info(f"🚀 Executing {len(pre_commands)} pre-commands...")
        
        for i, command in enumerate(pre_commands):
            final_command = self._substitute_template(command)
            self.logger.info(f"   Command {i+1}: {final_command}")
            
            docker_cmd = f"sudo docker exec {container_id} sh -c '{final_command}'"
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=60)
            
            if exit_code == 0:
                self.logger.info(f"   ✅ Pre-command {i+1} completed")
            else:
                self.logger.error(f"   ❌ Pre-command {i+1} failed: {stderr}")
                return False
        
        return True
    
    def _edit_files(self, container_id: str, file_edits: List[FileEdit]) -> bool:
        """Edit multiple files"""
        self.logger.info(f"📝 Editing {len(file_edits)} files...")
        
        for i, file_edit in enumerate(file_edits):
            if not self._edit_file(container_id, file_edit):
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
        self.logger.info(f"🔄 Executing {len(post_commands)} post-commands...")
        
        for i, command in enumerate(post_commands):
            final_command = self._substitute_template(command)
            self.logger.info(f"   Command {i+1}: {final_command}")
            
            docker_cmd = f"sudo docker exec {container_id} sh -c '{final_command}'"
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=60)
            
            if exit_code == 0:
                self.logger.info(f"   ✅ Post-command {i+1} completed")
            else:
                self.logger.warning(f"   ⚠️ Post-command {i+1} failed: {stderr}")
                # Don't return False for post-commands, just warn
        
        return True
    
    def execute_cleanup_commands(self, container_id: str, cleanup_commands: List[str], template_vars: Dict[str, str]):
        """Execute cleanup commands"""
        if not cleanup_commands:
            return
        
        self.set_template_variables(template_vars)
        self.logger.info(f"🧹 Executing {len(cleanup_commands)} cleanup commands...")
        
        for i, command in enumerate(cleanup_commands):
            final_command = self._substitute_template(command)
            self.logger.info(f"   Cleanup {i+1}: {final_command}")
            
            docker_cmd = f"sudo docker exec {container_id} sh -c '{final_command}'"
            exit_code, stdout, stderr = self.device.execute_command(docker_cmd, timeout=60)
            
            if exit_code == 0:
                self.logger.info(f"   ✅ Cleanup {i+1} completed")
            else:
                self.logger.warning(f"   ⚠️ Cleanup {i+1} failed: {stderr}")
    
    @staticmethod
    def parse_container_setup_config(config_dict: Dict[str, Any]) -> ContainerSetupConfig:
        """Parse container setup configuration from dictionary"""
        
        # Parse file edits
        file_edits = []
        if 'file_edits' in config_dict:
            for edit_dict in config_dict['file_edits']:
                file_edits.append(FileEdit(**edit_dict))
        
        return ContainerSetupConfig(
            pre_commands=config_dict.get('pre_commands', []),
            file_edits=file_edits,
            valgrind_command=config_dict.get('valgrind_command', ''),
            post_commands=config_dict.get('post_commands', []),
            cleanup_commands=config_dict.get('cleanup_commands', []),
            working_dir=config_dict.get('working_dir'),
            use_single_session=config_dict.get('use_single_session', True)
        ) 