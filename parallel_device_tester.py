#!/usr/bin/env python3
"""
Parallel Device Memory Tester
Configuration-driven testing of multiple devices and containers in parallel
"""

import argparse
import asyncio
import concurrent.futures
import logging
import sys
import yaml
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import queue

from src.device.device_connector import DeviceConfig, DeviceConnector
from src.device.containerized_profiler import ContainerizedProfiler
from src.device.netconf_client import NetconfConfig, RpcOperation

@dataclass
class TestScenario:
    """Configuration for a single test scenario"""
    name: str
    container_id: str
    process_pid: Optional[int] = None
    memory_limit: str = "5g"
    profiler: str = "valgrind"
    profiling_duration: int = 60
    restore_memory: bool = True
    netconf: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, str]] = None

@dataclass
class DeviceConfig:
    """Configuration for a device and its test scenarios"""
    name: str
    connection: Dict[str, Any]
    test_scenarios: List[TestScenario]

@dataclass
class TestResult:
    """Result of a test execution"""
    device_name: str
    scenario_name: str
    status: str  # "success", "failed", "skipped"
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    session_summary: Optional[Dict[str, Any]] = None
    output_files: List[str] = None

class ParallelDeviceTester:
    """Parallel device memory testing orchestrator"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = self._load_config()
        self.results: List[TestResult] = []
        self.setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate required sections
            if 'devices' not in config:
                raise ValueError("Configuration must contain 'devices' section")
            
            return config
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        """Setup logging configuration"""
        global_config = self.config.get('global_config', {})
        log_level = global_config.get('log_level', 'INFO')
        log_file = global_config.get('log_file', 'parallel_device_testing.log')
        
        # Create logs directory
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def list_devices_and_scenarios(self):
        """List all configured devices and test scenarios"""
        print("📋 CONFIGURED DEVICES AND TEST SCENARIOS")
        print("=" * 80)
        
        devices = self.config['devices']
        total_scenarios = 0
        
        for device_name, device_config in devices.items():
            scenarios = device_config.get('test_scenarios', [])
            total_scenarios += len(scenarios)
            
            print(f"\n🖥️  Device: {device_name}")
            print(f"   Host: {device_config['connection']['hostname']}")
            print(f"   User: {device_config['connection']['username']}")
            print(f"   Scenarios: {len(scenarios)}")
            
            for i, scenario in enumerate(scenarios, 1):
                print(f"     {i}. {scenario['name']}")
                print(f"        Container: {scenario['container_id']}")
                print(f"        Memory: {scenario.get('memory_limit', '5g')}")
                print(f"        Duration: {scenario.get('profiling_duration', 60)}s")
        
        global_config = self.config.get('global_config', {})
        max_parallel = global_config.get('max_parallel_devices', 1)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Devices: {len(devices)}")
        print(f"   Total Scenarios: {total_scenarios}")
        print(f"   Max Parallel Devices: {max_parallel}")
    
    def discover_all_devices(self):
        """Discover containers and processes on all devices"""
        print("🔍 DISCOVERING ALL DEVICES")
        print("=" * 80)
        
        devices = self.config['devices']
        
        for device_name, device_config in devices.items():
            print(f"\n🖥️  Discovering: {device_name}")
            print("-" * 60)
            
            try:
                conn_config = device_config['connection']
                device_conn_config = DeviceConfig(
                    hostname=conn_config['hostname'],
                    port=conn_config.get('port', 22),
                    username=conn_config['username'],
                    password=conn_config.get('password', ''),
                    key_file=conn_config.get('key_file', '')
                )
                
                with DeviceConnector(device_conn_config) as device:
                    profiler = ContainerizedProfiler(device)
                    containers_info = profiler.discover_containers_and_processes()
                    
                    if containers_info:
                        print(f"✅ Found {len(containers_info)} NETCONF containers:")
                        for container_name, info in containers_info.items():
                            container = info['container']
                            processes = info['processes']
                            print(f"   📦 {container_name}")
                            print(f"      Status: {container.status}")
                            print(f"      Memory: {container.memory_usage} / {container.memory_limit}")
                            print(f"      Processes: {len(processes)}")
                            for proc in processes[:3]:  # Show first 3 processes
                                print(f"        PID {proc.pid}: {proc.name}")
                    else:
                        print("❌ No NETCONF containers found")
                        
            except Exception as e:
                print(f"❌ Failed to discover {device_name}: {e}")
    
    def run_single_test(self, device_name: str, scenario: Dict[str, Any]) -> TestResult:
        """Run a single test scenario on a device"""
        scenario_name = scenario['name']
        start_time = datetime.now()
        
        result = TestResult(
            device_name=device_name,
            scenario_name=scenario_name,
            status="running",
            start_time=start_time
        )
        
        try:
            self.logger.info(f"Starting test: {device_name} - {scenario_name}")
            
            # Get device configuration
            device_config = self.config['devices'][device_name]
            conn_config = device_config['connection']
            
            device_conn_config = DeviceConfig(
                hostname=conn_config['hostname'],
                port=conn_config.get('port', 22),
                username=conn_config['username'],
                password=conn_config.get('password', ''),
                key_file=conn_config.get('key_file', '')
            )
            
            # Connect and run test
            with DeviceConnector(device_conn_config) as device:
                profiler = ContainerizedProfiler(device)
                
                # Auto-discover process if not specified
                process_pid = scenario.get('process_pid')
                if not process_pid:
                    containers_info = profiler.discover_containers_and_processes()
                    container_id = scenario['container_id']
                    
                    # Find matching container and get first process
                    for container_name, info in containers_info.items():
                        if container_id in container_name or container_id in info['container'].container_id:
                            if info['processes']:
                                process_pid = info['processes'][0].pid
                                self.logger.info(f"Auto-discovered process PID: {process_pid}")
                                break
                    
                    if not process_pid:
                        raise ValueError(f"Could not find process in container {container_id}")
                
                # Start profiling
                session = profiler.start_containerized_profiling(
                    container_id=scenario['container_id'],
                    process_pid=process_pid,
                    memory_limit=scenario.get('memory_limit', '5g'),
                    profiler_type=scenario.get('profiler', 'valgrind'),
                    session_id=scenario.get('output', {}).get('session_name', f"{device_name}_{scenario_name}")
                )
                
                if not session:
                    raise RuntimeError("Failed to start profiling session")
                
                # Wait for profiling duration
                duration = scenario.get('profiling_duration', 60)
                self.logger.info(f"Running profiling for {duration} seconds...")
                time.sleep(duration)
                
                # Stop profiling
                stop_success = profiler.stop_containerized_profiling(session.session_id)
                
                if stop_success:
                    # Download results
                    output_config = scenario.get('output', {})
                    output_dir = Path(output_config.get('output_dir', f'results/{device_name}'))
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    local_file = profiler.download_session_logs(session.session_id, output_dir)
                    
                    # Restore memory if requested
                    if scenario.get('restore_memory', True):
                        profiler.restore_container_memory(session.session_id)
                    
                    # Generate session summary
                    session_summary = {
                        "device_name": device_name,
                        "scenario_name": scenario_name,
                        "session_id": session.session_id,
                        "container_id": session.container_id,
                        "container_name": session.container_name,
                        "process_pid": session.process_pid,
                        "process_name": session.process_name,
                        "profiler_type": session.profiler_type,
                        "start_time": session.start_time.isoformat(),
                        "end_time": session.end_time.isoformat() if session.end_time else None,
                        "memory_increased": session.memory_increased,
                        "original_memory_limit": session.original_memory_limit,
                        "new_memory_limit": session.new_memory_limit,
                        "status": session.status,
                        "local_log_file": str(local_file) if local_file else None
                    }
                    
                    result.session_summary = session_summary
                    result.output_files = [str(local_file)] if local_file else []
                    result.status = "success"
                    
                    self.logger.info(f"Test completed successfully: {device_name} - {scenario_name}")
                else:
                    raise RuntimeError("Failed to stop profiling and collect results")
                    
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            self.logger.error(f"Test failed: {device_name} - {scenario_name}: {e}")
        
        result.end_time = datetime.now()
        return result
    
    def run_device_tests(self, device_name: str) -> List[TestResult]:
        """Run all test scenarios for a single device"""
        device_config = self.config['devices'][device_name]
        scenarios = device_config.get('test_scenarios', [])
        
        results = []
        global_config = self.config.get('global_config', {})
        max_parallel_tests = global_config.get('max_parallel_tests_per_device', 2)
        
        if len(scenarios) <= max_parallel_tests:
            # Run all scenarios in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_tests) as executor:
                futures = [executor.submit(self.run_single_test, device_name, scenario) 
                          for scenario in scenarios]
                
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
        else:
            # Run scenarios in batches
            for i in range(0, len(scenarios), max_parallel_tests):
                batch = scenarios[i:i + max_parallel_tests]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_tests) as executor:
                    futures = [executor.submit(self.run_single_test, device_name, scenario) 
                              for scenario in batch]
                    
                    for future in concurrent.futures.as_completed(futures):
                        results.append(future.result())
        
        return results
    
    def run_all_tests(self):
        """Run tests on all configured devices in parallel"""
        print("🚀 STARTING PARALLEL DEVICE TESTING")
        print("=" * 80)
        
        devices = list(self.config['devices'].keys())
        global_config = self.config.get('global_config', {})
        max_parallel_devices = global_config.get('max_parallel_devices', 3)
        
        print(f"📊 Testing {len(devices)} devices with max {max_parallel_devices} parallel")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_results = []
        
        # Run devices in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_devices) as executor:
            futures = {executor.submit(self.run_device_tests, device_name): device_name 
                      for device_name in devices}
            
            for future in concurrent.futures.as_completed(futures):
                device_name = futures[future]
                try:
                    device_results = future.result()
                    all_results.extend(device_results)
                    
                    # Print progress
                    success_count = sum(1 for r in device_results if r.status == "success")
                    total_count = len(device_results)
                    print(f"✅ Device {device_name} completed: {success_count}/{total_count} tests successful")
                    
                except Exception as e:
                    print(f"❌ Device {device_name} failed: {e}")
        
        self.results = all_results
        self._generate_consolidated_report()
        
        print(f"\n🎉 PARALLEL TESTING COMPLETED")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._print_summary()
    
    def _generate_consolidated_report(self):
        """Generate a consolidated report of all test results"""
        global_config = self.config.get('global_config', {})
        
        if not global_config.get('consolidated_report', True):
            return
        
        report_dir = Path(global_config.get('consolidated_report_dir', 'results/consolidated'))
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate JSON report
        report_data = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "config_file": str(self.config_file),
                "total_devices": len(self.config['devices']),
                "total_tests": len(self.results)
            },
            "results": [asdict(result) for result in self.results],
            "summary": self._generate_summary()
        }
        
        report_file = report_dir / f"consolidated_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        self.logger.info(f"Consolidated report generated: {report_file}")
        print(f"📄 Consolidated report: {report_file}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status == "failed")
        
        # Group by device
        device_summary = {}
        for result in self.results:
            if result.device_name not in device_summary:
                device_summary[result.device_name] = {"total": 0, "successful": 0, "failed": 0}
            
            device_summary[result.device_name]["total"] += 1
            if result.status == "success":
                device_summary[result.device_name]["successful"] += 1
            elif result.status == "failed":
                device_summary[result.device_name]["failed"] += 1
        
        return {
            "overall": {
                "total_tests": total,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
            },
            "by_device": device_summary
        }
    
    def _print_summary(self):
        """Print test execution summary"""
        summary = self._generate_summary()
        
        print(f"\n📊 TEST EXECUTION SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {summary['overall']['total_tests']}")
        print(f"Successful:  {summary['overall']['successful']}")
        print(f"Failed:      {summary['overall']['failed']}")
        print(f"Success Rate: {summary['overall']['success_rate']}")
        
        print(f"\n📋 BY DEVICE:")
        for device_name, stats in summary['by_device'].items():
            rate = f"{(stats['successful']/stats['total']*100):.1f}%" if stats['total'] > 0 else "0%"
            print(f"  {device_name}: {stats['successful']}/{stats['total']} ({rate})")

def main():
    parser = argparse.ArgumentParser(description='Parallel Device Memory Tester')
    
    parser.add_argument('--config', '-c', type=Path, required=True,
                       help='YAML configuration file')
    parser.add_argument('--list', action='store_true',
                       help='List configured devices and scenarios')
    parser.add_argument('--discover', action='store_true',
                       help='Discover containers on all devices')
    parser.add_argument('--device', '-d',
                       help='Run tests for specific device only')
    parser.add_argument('--scenario', '-s',
                       help='Run specific scenario only (requires --device)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be executed without running tests')
    
    args = parser.parse_args()
    
    if not args.config.exists():
        print(f"❌ Configuration file not found: {args.config}")
        return 1
    
    tester = ParallelDeviceTester(args.config)
    
    if args.list:
        tester.list_devices_and_scenarios()
        return 0
    
    if args.discover:
        tester.discover_all_devices()
        return 0
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No tests will be executed")
        tester.list_devices_and_scenarios()
        return 0
    
    if args.device:
        if args.device not in tester.config['devices']:
            print(f"❌ Device '{args.device}' not found in configuration")
            return 1
        
        if args.scenario:
            # Run single scenario
            device_config = tester.config['devices'][args.device]
            scenarios = device_config.get('test_scenarios', [])
            scenario = next((s for s in scenarios if s['name'] == args.scenario), None)
            
            if not scenario:
                print(f"❌ Scenario '{args.scenario}' not found for device '{args.device}'")
                return 1
            
            result = tester.run_single_test(args.device, scenario)
            print(f"Test result: {result.status}")
            if result.status == "failed":
                print(f"Error: {result.error_message}")
        else:
            # Run all scenarios for device
            results = tester.run_device_tests(args.device)
            success_count = sum(1 for r in results if r.status == "success")
            print(f"Device tests completed: {success_count}/{len(results)} successful")
    else:
        # Run all tests
        tester.run_all_tests()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 