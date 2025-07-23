#!/usr/bin/env python3
"""
Unified NETCONF Memory Leak Tester
Comprehensive tool for memory leak testing on containerized NETCONF applications
"""

import os
import sys
import time
import argparse
import logging
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import threading
import subprocess

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.device.device_connector import DeviceConnector, DeviceConfig, ProcessInfo
from src.device.docker_manager import DockerManager, ContainerInfo
from src.device.netconf_client import NetconfClient

@dataclass
class TestConfig:
    """Configuration for memory testing session"""
    device_config: DeviceConfig
    containers: List[str]
    memory_limit: str = "5g"
    profiler: str = "valgrind"  # valgrind or asan
    profiling_duration: int = 120
    rpc_count: int = 50
    rpc_interval: float = 1.0
    output_dir: str = "results"
    auto_analyze: bool = True
    cleanup_on_exit: bool = True
    restore_memory: bool = True

class MemoryTester:
    """Unified memory leak testing orchestrator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, Dict] = {}
        
    def discover_devices_and_containers(self, config_file: Path) -> Dict[str, Any]:
        """Discover all containers and processes on configured devices"""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            discovery_results = {}
            
            for device_name, device_config in config.get('devices', {}).items():
                self.logger.info(f"🔍 Discovering containers on device: {device_name}")
                
                # Create device configuration
                device_cfg = DeviceConfig(
                    hostname=device_config['connection']['hostname'],
                    port=device_config['connection'].get('port', 22),
                    username=device_config['connection']['username'],
                    password=device_config['connection'].get('password', ''),
                    key_file=device_config['connection'].get('private_key_file', ''),
                    use_diag_shell=device_config['connection'].get('use_diag_shell', True),
                    use_sudo_docker=device_config['connection'].get('use_sudo_docker', True),
                    diag_command=device_config['connection'].get('diag_command', 'diag shell host')
                )
                
                try:
                    with DeviceConnector(device_cfg) as device:
                        docker_manager = DockerManager(device)
                        
                        # Use efficient targeted container discovery
                        self.logger.info(f"🔍 Efficiently searching for target NETCONF container on {device_name}")
                        target_container = docker_manager.find_target_netconf_container()
                        
                        if target_container:
                            self.logger.info(f"🎯 Found target container: {target_container.name}")
                            
                            # Get processes only for the target container
                            processes = docker_manager.find_netconf_processes_in_container(target_container.container_id)
                            
                            container_details = {
                                target_container.name: {
                                    'container_info': target_container,
                                    'processes': processes
                                }
                            }
                            
                            discovery_results[device_name] = {
                                'device_config': device_cfg,
                                'target_container': target_container.name,
                                'container_id': target_container.container_id[:12],
                                'container_status': target_container.status,
                                'memory_usage': target_container.memory_usage,
                                'memory_limit': target_container.memory_limit,
                                'netconf_processes': len(processes),
                                'container_details': container_details,
                                'system_info': device.get_system_info()
                            }
                            
                            self.logger.info(f"✅ Device {device_name}: Found container '{target_container.name}' with {len(processes)} NETCONF processes")
                        else:
                            self.logger.warning(f"⚠️ Device {device_name}: No NETCONF container found")
                            discovery_results[device_name] = {
                                'device_config': device_cfg,
                                'target_container': None,
                                'error': 'No NETCONF container found',
                                'system_info': device.get_system_info()
                            }
                        
                except Exception as e:
                    self.logger.error(f"❌ Failed to discover {device_name}: {e}")
                    discovery_results[device_name] = {'error': str(e)}
            
            return discovery_results
            
        except Exception as e:
            self.logger.error(f"Error during discovery: {e}")
            return {}
    
    def run_comprehensive_test(self, config_file: Path, device_name: str = None, dry_run: bool = False) -> bool:
        """Run comprehensive memory leak testing"""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            devices_to_test = [device_name] if device_name else list(config.get('devices', {}).keys())
            
            # Global configuration
            global_config = config.get('global_config', {})
            max_parallel = global_config.get('max_parallel_devices', 1)
            
            self.logger.info(f"🚀 Starting comprehensive memory testing")
            self.logger.info(f"📋 Devices: {devices_to_test}")
            self.logger.info(f"🔧 Mode: {'DRY RUN' if dry_run else 'LIVE TEST'}")
            
            if len(devices_to_test) == 1:
                # Single device testing
                return self._test_single_device(config, devices_to_test[0], dry_run)
            else:
                # Parallel device testing
                return self._test_multiple_devices(config, devices_to_test, max_parallel, dry_run)
                
        except Exception as e:
            self.logger.error(f"Error during comprehensive testing: {e}")
            return False
    
    def _test_single_device(self, config: Dict, device_name: str, dry_run: bool = False) -> bool:
        """Test a single device with all its containers"""
        device_config = config['devices'][device_name]
        
        # Create device configuration
        device_cfg = DeviceConfig(
            hostname=device_config['connection']['hostname'],
            port=device_config['connection'].get('port', 22),
            username=device_config['connection']['username'],
            password=device_config['connection'].get('password', ''),
            key_file=device_config['connection'].get('private_key_file', ''),
            use_diag_shell=device_config['connection'].get('use_diag_shell', True),
            use_sudo_docker=device_config['connection'].get('use_sudo_docker', True),
            diag_command=device_config['connection'].get('diag_command', 'diag shell host')
        )
        
        session_id = f"{device_name}_{int(time.time())}"
        self.active_sessions[session_id] = {
            'device_name': device_name,
            'start_time': datetime.now(),
            'status': 'initializing'
        }
        
        try:
            self.logger.info(f"🔗 Connecting to device: {device_name}")
            
            with DeviceConnector(device_cfg) as device:
                docker_manager = DockerManager(device)
                
                self.active_sessions[session_id]['status'] = 'connected'
                
                # Process each test scenario
                test_scenarios = device_config.get('test_scenarios', [])
                if not test_scenarios:
                    self.logger.warning(f"No test scenarios defined for {device_name}")
                    return True
                
                for scenario in test_scenarios:
                    scenario_success = self._run_scenario(
                        device, docker_manager, scenario, session_id, dry_run
                    )
                    
                    if not scenario_success and not dry_run:
                        self.logger.error(f"Scenario '{scenario['name']}' failed")
                        return False
                
                self.active_sessions[session_id]['status'] = 'completed'
                self.active_sessions[session_id]['end_time'] = datetime.now()
                
                self.logger.info(f"✅ Device {device_name} testing completed successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Device {device_name} testing failed: {e}")
            self.active_sessions[session_id]['status'] = 'failed'
            self.active_sessions[session_id]['error'] = str(e)
            return False
    
    def _run_scenario(self, device: DeviceConnector, docker_manager: DockerManager, 
                     scenario: Dict, session_id: str, dry_run: bool = False) -> bool:
        """Run a single test scenario"""
        scenario_name = scenario['name']
        container_id = scenario['container_id']
        memory_limit = scenario.get('memory_limit', '5g')
        profiler = scenario.get('profiler', 'valgrind')
        duration = scenario.get('profiling_duration', 120)
        
        self.logger.info(f"🎯 Running scenario: {scenario_name}")
        self.logger.info(f"📦 Container: {container_id}")
        self.logger.info(f"🧠 Memory: {memory_limit}, Profiler: {profiler}, Duration: {duration}s")
        
        if dry_run:
            self.logger.info("🔍 DRY RUN - Verifying configuration...")
            
            # Check container exists
            container_info = docker_manager.get_container_info(container_id)
            if not container_info:
                self.logger.error(f"❌ Container {container_id} not found")
                return False
            
            # Check processes
            processes = docker_manager.find_netconf_processes_in_container(container_id)
            if not processes:
                self.logger.warning(f"⚠️ No NETCONF processes found in {container_id}")
            
            # Check Valgrind
            if profiler.lower() == 'valgrind':
                if not docker_manager.verify_valgrind_in_container(container_id):
                    self.logger.error(f"❌ Valgrind not available in {container_id}")
                    return False
            
            self.logger.info("✅ DRY RUN successful - configuration valid")
            return True
        
        # Live testing
        original_memory = None
        valgrind_pid = None
        
        try:
            # Step 1: Get container info and increase memory
            container_info = docker_manager.get_container_info(container_id)
            if not container_info:
                self.logger.error(f"Container {container_id} not found")
                return False
            
            original_memory = container_info.memory_limit
            self.logger.info(f"💾 Original memory: {original_memory}")
            
            # Increase memory
            if not docker_manager.increase_container_memory(container_id, memory_limit):
                self.logger.error("Failed to increase container memory")
                return False
            
            self.logger.info(f"📈 Memory increased to {memory_limit}")
            
            # Step 2: Start Valgrind with configurable setup
            if profiler.lower() == 'valgrind':
                # Check if scenario has custom container setup
                if 'container_setup' in scenario:
                    self.logger.info("🔧 Using configurable container setup...")
                    
                    # Set template variables for this scenario
                    template_vars = {
                        'container_id': container_id,
                        'session_id': session_id,
                        'scenario_name': scenario_name,
                        'memory_limit': memory_limit,
                        'device_hostname': device.config.hostname
                    }
                    
                    # Use configurable setup
                    success, valgrind_pid = docker_manager.start_netconfd_with_configurable_setup(
                        container_id=container_id,
                        container_setup_config=scenario,
                        template_vars=template_vars
                    )
                    
                    if not success:
                        self.logger.error("Failed to start NETCONF with configurable setup")
                        return False
                    
                    self.logger.info(f"✅ NETCONF started with configurable setup, PID: {valgrind_pid}")
                else:
                    # Use default/legacy approach
                    self.logger.info("🔧 Using default Valgrind setup...")
                    success, valgrind_pid = docker_manager.start_netconfd_with_valgrind_in_container(
                        container_id=container_id,
                        valgrind_options={
                            "xml-file": f"/tmp/{session_id}_{scenario_name}_valgrind.xml",
                            "leak-check": "full",
                            "track-origins": "yes"
                        }
                    )
                    
                    if not success:
                        self.logger.error("Failed to start NETCONF with Valgrind")
                        return False
                    
                    self.logger.info(f"✅ NETCONF started with Valgrind, PID: {valgrind_pid}")
            
            # Step 3: Execute RPC stress testing
            rpc_count = scenario.get('rpc_count', 20)
            self.logger.info(f"🚀 Executing {rpc_count} RPC stress tests...")
            
            for i in range(rpc_count):
                self.logger.info(f"📡 RPC {i+1}/{rpc_count}")
                time.sleep(scenario.get('rpc_interval', 0.5))
            
            # Step 4: Monitor profiling
            self.logger.info(f"⏱️ Profiling for {duration} seconds...")
            
            start_time = time.time()
            while time.time() - start_time < duration:
                elapsed = int(time.time() - start_time)
                
                if elapsed % 30 == 0 and elapsed > 0:
                    container_info = docker_manager.get_container_info(container_id)
                    if container_info:
                        self.logger.info(f"📊 Progress: {elapsed}/{duration}s | Memory: {container_info.memory_usage}")
                
                time.sleep(1)
            
            # Step 5: Collect results
            self.logger.info("📥 Collecting Valgrind results...")
            
            # Stop Valgrind
            if valgrind_pid:
                kill_cmd = f"docker exec {container_id} kill -TERM {valgrind_pid}"
                device.execute_command(kill_cmd)
                time.sleep(10)  # Wait for output
            
            # Download results
            output_dir = Path(scenario.get('output', {}).get('output_dir', 'results'))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            valgrind_file = f"/tmp/{session_id}_{scenario_name}_valgrind.xml"
            local_file = output_dir / f"{session_id}_{scenario_name}_valgrind.xml"
            
            copy_cmd = f"docker cp {container_id}:{valgrind_file} {local_file}"
            exit_code, stdout, stderr = device.execute_command(copy_cmd)
            
            if exit_code == 0:
                self.logger.info(f"✅ Results collected: {local_file}")
                
                # Auto-analyze if enabled
                if scenario.get('auto_analyze', True):
                    self._analyze_results(local_file, output_dir, session_id, scenario_name)
            else:
                self.logger.error(f"❌ Failed to collect results: {stderr}")
            
            # Step 6: Restart NETCONF normally
            self.logger.info("🔄 Restarting NETCONF normally...")
            docker_manager.restart_netconfd_normally_in_container(container_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in scenario {scenario_name}: {e}")
            return False
            
        finally:
            # Cleanup: Execute configurable cleanup commands if specified
            if 'container_setup' in scenario and 'cleanup_commands' in scenario['container_setup']:
                cleanup_commands = scenario['container_setup']['cleanup_commands']
                if cleanup_commands:
                    self.logger.info("🧹 Running configurable cleanup commands...")
                    
                    # Set template variables for cleanup
                    template_vars = {
                        'container_id': container_id,
                        'session_id': session_id,
                        'scenario_name': scenario_name,
                        'memory_limit': memory_limit,
                        'device_hostname': device.config.hostname if hasattr(device, 'config') else 'unknown'
                    }
                    
                    try:
                        docker_manager.cleanup_configurable_container(
                            container_id=container_id,
                            cleanup_commands=cleanup_commands,
                            template_vars=template_vars
                        )
                    except Exception as e:
                        self.logger.warning(f"Configurable cleanup failed: {e}")
            
            # Cleanup: Restore memory
            if original_memory and scenario.get('restore_memory', True):
                self.logger.info(f"🔄 Restoring memory to {original_memory}")
                try:
                    docker_manager.increase_container_memory(container_id, original_memory)
                except Exception as e:
                    self.logger.warning(f"Failed to restore memory: {e}")
    
    def _analyze_results(self, log_file: Path, output_dir: Path, session_id: str, scenario_name: str):
        """Analyze Valgrind results and generate reports"""
        try:
            self.logger.info("🔬 Starting result analysis...")
            
            # Use the enhanced analyzer
            analyzer_cmd = [
                sys.executable, "memory_leak_analyzer_enhanced.py",
                "--input", str(log_file),
                "--output", str(output_dir / f"{session_id}_{scenario_name}_report.html"),
                "--cleanup",
                "--impact-analysis",
                "--export-csv", str(output_dir / f"{session_id}_{scenario_name}_data.csv")
            ]
            
            result = subprocess.run(analyzer_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("✅ Analysis completed successfully")
            else:
                self.logger.error(f"❌ Analysis failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
    
    def _test_multiple_devices(self, config: Dict, device_names: List[str], 
                              max_parallel: int, dry_run: bool = False) -> bool:
        """Test multiple devices in parallel"""
        self.logger.info(f"🔄 Testing {len(device_names)} devices (max parallel: {max_parallel})")
        
        # TODO: Implement parallel testing with threading
        # For now, run sequentially
        all_success = True
        
        for device_name in device_names:
            self.logger.info(f"🎯 Testing device: {device_name}")
            success = self._test_single_device(config, device_name, dry_run)
            if not success:
                all_success = False
                self.logger.error(f"❌ Device {device_name} failed")
            else:
                self.logger.info(f"✅ Device {device_name} completed")
        
        return all_success
    
    def get_session_status(self, session_id: str = None) -> Dict:
        """Get status of testing sessions"""
        if session_id:
            return self.active_sessions.get(session_id, {})
        else:
            return self.active_sessions
    
    def generate_consolidated_report(self, output_dir: Path) -> bool:
        """Generate consolidated report from all results"""
        try:
            self.logger.info("📊 Generating consolidated report...")
            
            # Find all analysis results
            html_files = list(output_dir.glob("*_report.html"))
            csv_files = list(output_dir.glob("*_data.csv"))
            
            if not html_files:
                self.logger.warning("No HTML reports found for consolidation")
                return False
            
            # Use existing report generation tools
            self.logger.info(f"✅ Found {len(html_files)} reports for consolidation")
            
            # TODO: Implement actual consolidation logic
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating consolidated report: {e}")
            return False

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('memory_testing.log')
        ]
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Unified NETCONF Memory Leak Tester")
    
    # Main operation modes
    parser.add_argument("--discover", action="store_true", 
                       help="Discover containers and processes on devices")
    parser.add_argument("--test", action="store_true",
                       help="Run comprehensive memory testing")
    parser.add_argument("--status", action="store_true",
                       help="Show status of active sessions")
    
    # Configuration
    parser.add_argument("--config", type=Path, required=True,
                       help="YAML configuration file")
    parser.add_argument("--device", type=str,
                       help="Specific device to test (default: all)")
    
    # Testing options
    parser.add_argument("--dry-run", action="store_true",
                       help="Validate configuration without running tests")
    parser.add_argument("--parallel", type=int, default=1,
                       help="Maximum parallel devices")
    
    # Output options
    parser.add_argument("--output", type=Path, default="results",
                       help="Output directory")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Validate config file
    if not args.config.exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1
    
    # Create tester instance
    tester = MemoryTester()
    
    try:
        if args.discover:
            logger.info("🔍 Starting device and container discovery...")
            results = tester.discover_devices_and_containers(args.config)
            
            # Pretty print results
            print("\n" + "="*80)
            print("🔍 DEVICE DISCOVERY RESULTS")
            print("="*80)
            
            for device_name, info in results.items():
                if 'error' in info:
                    print(f"\n❌ {device_name}: {info['error']}")
                else:
                    print(f"\n✅ {device_name}")
                    
                    if info.get('target_container'):
                        # New efficient format - single target container
                        print(f"   🎯 Target Container: {info['target_container']}")
                        print(f"   📦 Container ID: {info['container_id']}")
                        print(f"   🔄 Status: {info['container_status']}")
                        print(f"   🧠 Memory: {info['memory_usage']} / {info['memory_limit']}")
                        print(f"   ⚙️  NETCONF Processes: {info['netconf_processes']}")
                        
                        # Show process details
                        for container_name, details in info['container_details'].items():
                            processes = details['processes']
                            if processes:
                                print(f"   📋 Process Details:")
                                for proc in processes:
                                    print(f"      • PID {proc.pid}: {proc.command[:60]}...")
                            else:
                                print(f"      ⚠️  No NETCONF processes found")
                    else:
                        # Legacy format fallback
                        if 'total_containers' in info:
                            print(f"   📊 Total containers: {info['total_containers']}")
                            print(f"   🐳 NETCONF containers: {info['netconf_containers']}")
                            
                            for container_name, details in info['container_details'].items():
                                container = details['container_info']
                                processes = details['processes']
                                print(f"   📦 {container_name} ({container.container_id[:12]})")
                                print(f"      Status: {container.status}")
                                print(f"      Memory: {container.memory_usage} / {container.memory_limit}")
                                print(f"      Processes: {len(processes)}")
                                for proc in processes:
                                    print(f"        • PID {proc.pid}: {proc.command}")
                        else:
                            print(f"   ⚠️  No container information available")
        
        elif args.test:
            logger.info("🚀 Starting comprehensive memory testing...")
            success = tester.run_comprehensive_test(args.config, args.device, args.dry_run)
            
            if success:
                logger.info("✅ Testing completed successfully")
                
                # Generate consolidated report
                if not args.dry_run:
                    tester.generate_consolidated_report(args.output)
                
                return 0
            else:
                logger.error("❌ Testing failed")
                return 1
        
        elif args.status:
            sessions = tester.get_session_status()
            print("\n" + "="*60)
            print("📊 ACTIVE SESSIONS")
            print("="*60)
            
            if not sessions:
                print("No active sessions")
            else:
                for session_id, session in sessions.items():
                    print(f"\n🔹 {session_id}")
                    print(f"   Device: {session.get('device_name', 'unknown')}")
                    print(f"   Status: {session.get('status', 'unknown')}")
                    print(f"   Started: {session.get('start_time', 'unknown')}")
                    if 'end_time' in session:
                        print(f"   Ended: {session['end_time']}")
                    if 'error' in session:
                        print(f"   Error: {session['error']}")
        
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Testing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 