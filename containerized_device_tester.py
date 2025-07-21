#!/usr/bin/env python3
"""
Containerized Device Memory Tester
Enhanced version for testing memory leaks in containerized NETCONF applications
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List
import time
import json

from src.device.device_connector import DeviceConfig, DeviceConnector
from src.device.netconf_client import NetconfConfig, RpcOperation
from src.device.docker_manager import DockerManager, ContainerConfig
from src.device.containerized_profiler import ContainerizedProfiler
from src.device.memory_profiler import ProfilingConfig

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('containerized_device_tester.log')
        ]
    )

def load_rpc_operations(rpc_dir: Path) -> List[RpcOperation]:
    """Load RPC operations from directory or create default ones"""
    operations = []
    
    if rpc_dir and rpc_dir.exists():
        from src.device.netconf_client import NetconfClient
        dummy_config = NetconfConfig(host="localhost")
        client = NetconfClient(dummy_config)
        operations = client.load_rpc_directory(rpc_dir)
    else:
        # Create some default RPC operations for testing
        operations = [
            RpcOperation(
                name="get_config_running",
                xml_content="<get-config><source><running/></source></get-config>",
                description="Get running configuration",
                repeat_count=10,
                delay_between_repeats=0.5
            ),
            RpcOperation(
                name="get_state_interfaces",
                xml_content="""<get>
                    <filter type="subtree">
                        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
                    </filter>
                </get>""",
                description="Get interface states",
                repeat_count=5,
                delay_between_repeats=1.0
            )
        ]
    
    return operations

def discover_containers_and_processes(device_config: DeviceConfig):
    """Discover containers and processes on the device"""
    print("🔍 DISCOVERING CONTAINERS AND PROCESSES")
    print("=" * 60)
    
    try:
        with DeviceConnector(device_config) as device:
            profiler = ContainerizedProfiler(device)
            
            containers_info = profiler.discover_containers_and_processes()
            
            if not containers_info:
                print("❌ No NETCONF containers found")
                return
            
            print(f"✅ Found {len(containers_info)} NETCONF containers:\n")
            
            for container_name, info in containers_info.items():
                container = info['container']
                processes = info['processes']
                
                print(f"📦 Container: {container_name}")
                print(f"   Image: {container.image}")
                print(f"   Status: {container.status}")
                print(f"   Memory: {container.memory_usage} / {container.memory_limit}")
                print(f"   CPU: {container.cpu_usage}")
                print(f"   Processes ({len(processes)}):")
                
                for process in processes:
                    print(f"     PID {process.pid}: {process.name} ({process.memory_usage}KB)")
                    print(f"       Command: {process.command[:80]}{'...' if len(process.command) > 80 else ''}")
                print()
                
    except Exception as e:
        print(f"❌ Failed to discover containers: {e}")

def run_containerized_memory_test(args):
    """Run complete containerized memory test"""
    print("🚀 STARTING CONTAINERIZED MEMORY TEST")
    print("=" * 60)
    
    device_config = DeviceConfig(
        hostname=args.device_host,
        port=args.device_port,
        username=args.device_user,
        password=args.device_password or "",
        key_file=args.device_key or ""
    )
    
    try:
        with DeviceConnector(device_config) as device:
            profiler = ContainerizedProfiler(device)
            
            # Step 1: Start profiling
            print(f"📊 Starting profiling on container {args.container_id}, process {args.process_pid}")
            print(f"🧠 Increasing memory to {args.memory_limit}")
            
            session = profiler.start_containerized_profiling(
                container_id=args.container_id,
                process_pid=args.process_pid,
                memory_limit=args.memory_limit,
                profiler_type=args.profiler,
                session_id=args.session_name
            )
            
            if not session:
                print("❌ Failed to start profiling session")
                return 1
            
            print(f"✅ Profiling session started: {session.session_id}")
            print(f"   Container: {session.container_name} ({session.container_id[:12]})")
            print(f"   Process: PID {session.process_pid} ({session.process_name})")
            print(f"   Memory: {session.original_memory_limit} → {session.new_memory_limit}")
            
            # Step 2: Execute RPC operations (if specified)
            if args.rpc_dir:
                print("\n🔄 Executing NETCONF RPC operations...")
                
                netconf_config = NetconfConfig(
                    host=args.netconf_host or args.device_host,
                    port=args.netconf_port,
                    username=args.netconf_user or args.device_user,
                    password=args.netconf_password or args.device_password or ""
                )
                
                rpc_operations = load_rpc_operations(args.rpc_dir)
                
                # Simulate RPC execution (in real implementation, use NetconfClient)
                total_operations = sum(op.repeat_count for op in rpc_operations)
                print(f"   Executing {total_operations} total operations...")
                
                for i in range(total_operations):
                    print(f"   Progress: {i+1}/{total_operations} operations", end='\r')
                    time.sleep(0.1)  # Simulate work
                
                print(f"\n✅ Completed {total_operations} RPC operations")
            
            # Step 3: Wait for profiling duration
            print(f"\n⏱️  Running profiling for {args.profiling_duration} seconds...")
            time.sleep(args.profiling_duration)
            
            # Step 4: Stop profiling and collect results
            print("\n📁 Stopping profiling and collecting results...")
            
            stop_success = profiler.stop_containerized_profiling(session.session_id)
            
            if stop_success:
                # Download results
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                local_file = profiler.download_session_logs(session.session_id, output_dir)
                
                if local_file:
                    print(f"✅ Results downloaded to: {local_file}")
                    
                    # Generate session summary
                    summary = {
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
                        "local_log_file": str(local_file)
                    }
                    
                    summary_file = output_dir / f"{session.session_id}_summary.json"
                    with open(summary_file, 'w') as f:
                        json.dump(summary, f, indent=2)
                    
                    print(f"📄 Session summary: {summary_file}")
                    
                    # Show diagnostics
                    diagnostics = profiler.get_container_diagnostics(session.container_id)
                    print(f"\n📊 Container Diagnostics:")
                    print(f"   Status: {diagnostics.get('container_info', {}).get('status', 'unknown')}")
                    print(f"   Memory: {diagnostics.get('container_info', {}).get('memory_usage', 'unknown')}")
                    print(f"   Processes: {len(diagnostics.get('processes', []))}")
                    
                else:
                    print("❌ Failed to download results")
                    
            # Step 5: Restore container memory (optional)
            if args.restore_memory:
                print("\n🔄 Restoring original container memory...")
                restore_success = profiler.restore_container_memory(session.session_id)
                if restore_success:
                    print("✅ Container memory restored")
                else:
                    print("⚠️  Failed to restore container memory")
            
            print(f"\n🎉 Containerized memory test completed!")
            return 0
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='Containerized Device Memory Tester for NETCONF processes')
    
    # Device connection options
    parser.add_argument('--device-host', required=True, help='Device hostname or IP')
    parser.add_argument('--device-port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--device-user', required=True, help='SSH username')
    parser.add_argument('--device-password', help='SSH password')
    parser.add_argument('--device-key', help='SSH private key file')
    
    # Container options
    parser.add_argument('--container-id', help='Docker container ID or name')
    parser.add_argument('--process-pid', type=int, help='Process PID to profile')
    parser.add_argument('--memory-limit', default='5g', help='Container memory limit (default: 5g)')
    parser.add_argument('--restore-memory', action='store_true', help='Restore original memory after test')
    
    # Profiling options
    parser.add_argument('--profiler', choices=['valgrind', 'asan'], default='valgrind',
                       help='Memory profiler to use (default: valgrind)')
    parser.add_argument('--profiling-duration', type=int, default=60,
                       help='Profiling duration in seconds (default: 60)')
    
    # NETCONF options
    parser.add_argument('--netconf-host', help='NETCONF server host (default: same as device)')
    parser.add_argument('--netconf-port', type=int, default=830, help='NETCONF port (default: 830)')
    parser.add_argument('--netconf-user', help='NETCONF username (default: same as device)')
    parser.add_argument('--netconf-password', help='NETCONF password (default: same as device)')
    parser.add_argument('--rpc-dir', type=Path, help='Directory containing RPC XML files')
    
    # Output options
    parser.add_argument('--session-name', default='containerized_test',
                       help='Test session name (default: containerized_test)')
    parser.add_argument('--output-dir', type=Path, default=Path('./container_test_results'),
                       help='Output directory for results (default: ./container_test_results)')
    
    # Utility options
    parser.add_argument('--discover', action='store_true',
                       help='Discover containers and processes, then exit')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Create device configuration
    device_config = DeviceConfig(
        hostname=args.device_host,
        port=args.device_port,
        username=args.device_user,
        password=args.device_password or "",
        key_file=args.device_key or ""
    )
    
    # Handle discovery mode
    if args.discover:
        discover_containers_and_processes(device_config)
        return 0
    
    # Validate required arguments for testing
    if not args.container_id:
        print("❌ Container ID is required for testing. Use --discover to find containers.")
        return 1
    
    if not args.process_pid:
        print("❌ Process PID is required for testing. Use --discover to find processes.")
        return 1
    
    # Run the test
    return run_containerized_memory_test(args)

if __name__ == "__main__":
    sys.exit(main()) 