"""
Integration Manager for Memory Leak Testing
Orchestrates the complete workflow of device connection, profiling, NETCONF testing, and analysis
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json
import subprocess

from .device_connector import DeviceConnector, DeviceConfig, ProcessInfo
from .memory_profiler import MemoryProfiler, ProfilingSession, ProfilingConfig
from .netconf_client import NetconfClient, NetconfConfig, RpcOperation
from ..models.leak_data import LeakDatabase
from ..parsers.valgrind_parser import ValgrindParser
from ..parsers.asan_parser import AsanParser

@dataclass
class TestSession:
    """Complete memory leak testing session"""
    session_id: str
    device_config: DeviceConfig
    netconf_config: NetconfConfig
    profiling_config: ProfilingConfig
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "initializing"  # initializing, running, completed, failed
    target_process: Optional[ProcessInfo] = None
    profiling_session: Optional[ProfilingSession] = None
    rpc_results: Dict[str, List[Dict[str, Any]]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    local_log_path: Optional[Path] = None

@dataclass 
class TestConfig:
    """Configuration for memory leak testing"""
    session_name: str
    device_config: DeviceConfig
    netconf_config: NetconfConfig
    profiling_config: ProfilingConfig
    rpc_operations: List[RpcOperation]
    output_directory: Path
    cleanup_remote_files: bool = True
    auto_analyze: bool = True
    generate_reports: bool = True

class IntegrationManager:
    """Manages the complete memory leak testing workflow"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, TestSession] = {}
    
    def start_test_session(self, config: TestConfig) -> Optional[str]:
        """Start a complete memory leak testing session"""
        session_id = f"{config.session_name}_{int(time.time())}"
        
        session = TestSession(
            session_id=session_id,
            device_config=config.device_config,
            netconf_config=config.netconf_config,
            profiling_config=config.profiling_config,
            start_time=datetime.now(),
            rpc_results={}
        )
        
        self.active_sessions[session_id] = session
        
        try:
            self.logger.info(f"Starting test session: {session_id}")
            
            # Step 1: Connect to device
            session.status = "connecting"
            if not self._connect_to_device(session, config):
                session.status = "failed"
                return None
            
            # Step 2: Find target process
            session.status = "finding_process"
            if not self._find_target_process(session, config):
                session.status = "failed" 
                return None
            
            # Step 3: Start memory profiling
            session.status = "starting_profiling"
            if not self._start_profiling(session, config):
                session.status = "failed"
                return None
            
            # Step 4: Execute NETCONF operations
            session.status = "running_tests"
            if not self._execute_netconf_operations(session, config):
                session.status = "failed"
                return None
            
            # Step 5: Stop profiling and collect logs
            session.status = "collecting_logs"
            if not self._collect_profiling_results(session, config):
                session.status = "failed"
                return None
            
            # Step 6: Analyze results
            if config.auto_analyze:
                session.status = "analyzing"
                self._analyze_results(session, config)
            
            # Step 7: Generate reports
            if config.generate_reports:
                session.status = "generating_reports"
                self._generate_reports(session, config)
            
            session.status = "completed"
            session.end_time = datetime.now()
            
            self.logger.info(f"Test session {session_id} completed successfully")
            return session_id
            
        except Exception as e:
            session.status = "failed"
            session.end_time = datetime.now()
            self.logger.error(f"Test session {session_id} failed: {e}")
            return None
    
    def get_session_status(self, session_id: str) -> Optional[TestSession]:
        """Get status of a test session"""
        return self.active_sessions.get(session_id)
    
    def stop_session(self, session_id: str) -> bool:
        """Stop a running test session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            # Stop profiling if running
            if session.profiling_session and session.profiling_session.status == "running":
                with DeviceConnector(session.device_config) as device:
                    profiler = MemoryProfiler(device)
                    profiler.stop_profiling_session(session.profiling_session.session_id)
            
            session.status = "stopped"
            session.end_time = datetime.now()
            
            self.logger.info(f"Stopped test session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop session {session_id}: {e}")
            return False
    
    def _connect_to_device(self, session: TestSession, config: TestConfig) -> bool:
        """Connect to the target device"""
        try:
            with DeviceConnector(config.device_config) as device:
                system_info = device.get_system_info()
                self.logger.info(f"Connected to device: {system_info.get('hostname', 'unknown')}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to connect to device: {e}")
            return False
    
    def _find_target_process(self, session: TestSession, config: TestConfig) -> bool:
        """Find the target NETCONF process"""
        try:
            with DeviceConnector(config.device_config) as device:
                processes = device.find_netconf_processes()
                
                if not processes:
                    self.logger.error("No NETCONF processes found on device")
                    return False
                
                # For now, select the first NETCONF process
                # In practice, you might want to select based on specific criteria
                session.target_process = processes[0]
                
                self.logger.info(f"Selected target process: PID {session.target_process.pid} ({session.target_process.name})")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to find target process: {e}")
            return False
    
    def _start_profiling(self, session: TestSession, config: TestConfig) -> bool:
        """Start memory profiling on the target process"""
        try:
            with DeviceConnector(config.device_config) as device:
                profiler = MemoryProfiler(device)
                profiler.config = config.profiling_config
                
                if config.profiling_config.profiler_type == "valgrind":
                    profiling_session = profiler.start_valgrind_profiling(
                        session.target_process.pid,
                        f"{session.session_id}_profiling"
                    )
                else:
                    profiling_session = profiler.start_asan_profiling(
                        session.target_process.pid,
                        f"{session.session_id}_profiling"
                    )
                
                if profiling_session:
                    session.profiling_session = profiling_session
                    self.logger.info(f"Started {config.profiling_config.profiler_type} profiling")
                    return True
                else:
                    self.logger.error("Failed to start profiling")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to start profiling: {e}")
            return False
    
    def _execute_netconf_operations(self, session: TestSession, config: TestConfig) -> bool:
        """Execute NETCONF RPC operations"""
        try:
            with NetconfClient(config.netconf_config) as netconf:
                self.logger.info(f"Executing {len(config.rpc_operations)} RPC operations")
                
                session.rpc_results = netconf.execute_rpc_sequence(config.rpc_operations)
                
                # Log summary
                total_ops = sum(len(results) for results in session.rpc_results.values())
                successful_ops = sum(
                    len([r for r in results if r['status'] == 'success']) 
                    for results in session.rpc_results.values()
                )
                
                self.logger.info(f"Completed {successful_ops}/{total_ops} RPC operations successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to execute NETCONF operations: {e}")
            return False
    
    def _collect_profiling_results(self, session: TestSession, config: TestConfig) -> bool:
        """Stop profiling and collect results"""
        try:
            with DeviceConnector(config.device_config) as device:
                profiler = MemoryProfiler(device)
                
                # Stop profiling
                if session.profiling_session:
                    profiler.stop_profiling_session(session.profiling_session.session_id)
                    
                    # Wait a bit for final output
                    time.sleep(5)
                    
                    # Download logs
                    config.output_directory.mkdir(parents=True, exist_ok=True)
                    local_path = profiler.download_session_logs(
                        session.profiling_session.session_id,
                        config.output_directory
                    )
                    
                    if local_path:
                        session.local_log_path = local_path
                        self.logger.info(f"Downloaded profiling logs to {local_path}")
                        
                        # Cleanup remote files if requested
                        if config.cleanup_remote_files:
                            profiler.cleanup_remote_files(session.profiling_session.session_id)
                        
                        return True
                    else:
                        self.logger.error("Failed to download profiling logs")
                        return False
                else:
                    self.logger.error("No profiling session to collect")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to collect profiling results: {e}")
            return False
    
    def _analyze_results(self, session: TestSession, config: TestConfig):
        """Analyze the collected memory profiling results"""
        if not session.local_log_path:
            self.logger.error("No local log file to analyze")
            return
        
        try:
            # Create leak database
            leak_db = LeakDatabase()
            
            # Parse the log file
            if config.profiling_config.profiler_type == "valgrind":
                parser = ValgrindParser()
                leaks = parser.parse_file(session.local_log_path)
            else:
                parser = AsanParser()
                leaks = parser.parse_file(session.local_log_path)
            
            leak_db.add_leaks(leaks)
            
            # Get statistics
            stats = leak_db.get_statistics()
            
            session.analysis_results = {
                "total_leaks": stats['total_leaks'],
                "total_bytes": stats['total_bytes'],
                "by_severity": stats['by_severity'],
                "by_type": stats['by_type'],
                "analyzer_version": config.profiling_config.profiler_type
            }
            
            self.logger.info(f"Analysis completed: {stats['total_leaks']} leaks found, {stats['total_bytes']:,} bytes")
            
        except Exception as e:
            self.logger.error(f"Failed to analyze results: {e}")
    
    def _generate_reports(self, session: TestSession, config: TestConfig):
        """Generate analysis reports"""
        if not session.local_log_path:
            return
        
        try:
            from ..reports.html_generator import HTMLGenerator
            from ..exports.csv_exporter import CSVExporter
            
            # Create leak database
            leak_db = LeakDatabase()
            
            # Parse the log file
            if config.profiling_config.profiler_type == "valgrind":
                parser = ValgrindParser()
                leaks = parser.parse_file(session.local_log_path)
            else:
                parser = AsanParser()
                leaks = parser.parse_file(session.local_log_path)
            
            leak_db.add_leaks(leaks)
            
            # Generate HTML report
            html_file = config.output_directory / f"{session.session_id}_report.html"
            html_generator = HTMLGenerator()
            html_generator.generate_report(leak_db, html_file)
            
            # Generate CSV export
            csv_file = config.output_directory / f"{session.session_id}_data.csv"
            csv_exporter = CSVExporter()
            csv_exporter.export_leaks(leak_db, csv_file)
            
            self.logger.info(f"Generated reports: {html_file}, {csv_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate reports: {e}")
    
    def export_session_summary(self, session_id: str, output_file: Path) -> bool:
        """Export a complete session summary"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        try:
            summary = {
                "session_id": session.session_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "status": session.status,
                "device": {
                    "hostname": session.device_config.hostname,
                    "port": session.device_config.port
                },
                "target_process": {
                    "pid": session.target_process.pid if session.target_process else None,
                    "name": session.target_process.name if session.target_process else None,
                    "command": session.target_process.command if session.target_process else None
                } if session.target_process else None,
                "profiling": {
                    "type": session.profiling_session.profiler_type if session.profiling_session else None,
                    "output_file": session.profiling_session.output_file if session.profiling_session else None
                } if session.profiling_session else None,
                "rpc_results": session.rpc_results,
                "analysis_results": session.analysis_results,
                "local_log_path": str(session.local_log_path) if session.local_log_path else None
            }
            
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.logger.info(f"Exported session summary to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export session summary: {e}")
            return False 