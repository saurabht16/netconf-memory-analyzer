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
import os

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

def run_containerized_memory_test(device_host: str, device_user: str, device_password: str,
                                 container_id: str, process_pid: int = None, memory_limit: str = "5g",
                                 profiler: str = "valgrind", session_name: str = None,
                                 profiling_duration: int = 60, output_dir: str = "results") -> bool:
    """
    Run memory test on containerized application with complete process restart
    """
    if session_name is None:
        session_name = f"container_test_{int(time.time())}"
    
    logger.info(f"🚀 Starting containerized memory test: {session_name}")
    logger.info(f"📊 Target: {device_host}, Container: {container_id}")
    logger.info(f"🧠 Memory: {memory_limit}, Profiler: {profiler}, Duration: {profiling_duration}s")
    
    # Device configuration with network device support
    device_config = DeviceConfig(
        hostname=device_host,
        username=device_user,
        password=device_password,
        use_diag_shell=True,        # Enable for network devices
        use_sudo_docker=True,       # Enable sudo for Docker commands
        diag_command="diag shell host"  # Network device diagnostic command
    )
    
    device = DeviceConnector(device_config)
    docker_manager = None
    original_memory_limit = None
    valgrind_pid = None
    
    try:
        # Step 1: Connect to device
        logger.info("🔗 Step 1: Connecting to device...")
        if not device.connect():
            logger.error("❌ Failed to connect to device")
            return False
        
        # Step 2: Initialize Docker manager
        logger.info("🐳 Step 2: Initializing Docker manager...")
        docker_manager = DockerManager(device)
        
        # Step 3: Get container info and increase memory
        logger.info(f"📦 Step 3: Getting container information: {container_id}")
        container_info = docker_manager.get_container_info(container_id)
        if not container_info:
            logger.error(f"❌ Container {container_id} not found")
            return False
        
        original_memory_limit = container_info.memory_limit
        logger.info(f"💾 Current memory limit: {original_memory_limit}")
        
        # Increase container memory
        logger.info(f"📈 Increasing container memory to {memory_limit}")
        if not docker_manager.increase_container_memory(container_id, memory_limit):
            logger.error("❌ Failed to increase container memory")
            return False
        
        logger.info(f"✅ Container memory increased to {memory_limit}")
        
        # Step 4: Show existing NETCONF processes before killing
        logger.info("🔍 Step 4: Discovering existing NETCONF processes...")
        existing_processes = docker_manager.find_netconf_processes_in_container(container_id)
        
        if existing_processes:
            logger.info(f"📋 Found {len(existing_processes)} existing NETCONF processes:")
            for proc in existing_processes:
                logger.info(f"   • PID {proc.pid}: {proc.command}")
        else:
            logger.info("ℹ️ No existing NETCONF processes found")
        
        # Step 5: Kill existing netconfd and start fresh with Valgrind
        logger.info("🎯 Step 5: Starting fresh netconfd with Valgrind...")
        
        if profiler.lower() == "valgrind":
            # Custom Valgrind options for comprehensive memory analysis
            valgrind_options = {
                "xml-file": f"/tmp/{session_name}_valgrind.xml",
                "leak-check": "full",
                "show-leak-kinds": "all",
                "track-origins": "yes",
                "gen-suppressions": "all",
                "child-silent-after-fork": "yes",
                "trace-children": "yes"
            }
            
            # Start fresh netconfd with Valgrind (this kills existing processes)
            success, valgrind_pid = docker_manager.start_netconfd_with_valgrind_in_container(
                container_id=container_id,
                netconfd_command="/usr/bin/netconfd --foreground",
                valgrind_options=valgrind_options
            )
            
            if not success:
                logger.error("❌ Failed to start netconfd with Valgrind")
                return False
                
            logger.info(f"✅ netconfd started fresh with Valgrind, PID: {valgrind_pid}")
            
        elif profiler.lower() == "asan":
            logger.error("❌ AddressSanitizer restart not implemented yet")
            return False
        else:
            logger.error(f"❌ Unknown profiler: {profiler}")
            return False
        
        # Step 6: Execute NETCONF RPC stress testing (optional)
        logger.info("🚀 Step 6: Executing NETCONF RPC stress testing...")
        rpc_count = 20  # Number of RPCs to execute
        
        for i in range(rpc_count):
            # Simulate NETCONF RPC calls
            logger.info(f"📡 Executing RPC {i+1}/{rpc_count}")
            time.sleep(0.5)  # Brief pause between RPCs
        
        logger.info(f"✅ Completed {rpc_count} RPC operations")
        
        # Step 7: Monitor profiling session
        logger.info(f"⏱️ Step 7: Monitoring profiling session for {profiling_duration} seconds...")
        
        start_time = time.time()
        while time.time() - start_time < profiling_duration:
            elapsed = int(time.time() - start_time)
            remaining = profiling_duration - elapsed
            
            # Show progress every 15 seconds
            if elapsed % 15 == 0 and elapsed > 0:
                container_info = docker_manager.get_container_info(container_id)
                if container_info:
                    logger.info(f"📊 Progress: {elapsed}s/{profiling_duration}s | Memory: {container_info.memory_usage}/{container_info.memory_limit}")
                
                # Verify Valgrind process is still running
                if valgrind_pid and not docker_manager.is_process_running_in_container(container_id, valgrind_pid):
                    logger.warning(f"⚠️ Valgrind process {valgrind_pid} is no longer running!")
            
            time.sleep(1)
        
        # Step 8: Stop Valgrind and collect results
        logger.info("📥 Step 8: Stopping Valgrind and collecting results...")
        
        if valgrind_pid:
            logger.info(f"🛑 Stopping Valgrind process PID {valgrind_pid}")
            # Send TERM signal to Valgrind process
            kill_cmd = f"docker exec {container_id} kill -TERM {valgrind_pid}"
            exit_code, stdout, stderr = device.execute_command(kill_cmd)
            
            if exit_code == 0:
                logger.info("✅ TERM signal sent to Valgrind process")
            else:
                logger.warning(f"⚠️ Failed to send TERM signal: {stderr}")
            
            # Wait for Valgrind to write output
            logger.info("⏱️ Waiting for Valgrind to write output...")
            time.sleep(10)
        
        # Step 9: Collect Valgrind output
        logger.info("📄 Step 9: Collecting Valgrind output...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        valgrind_internal_file = f"/tmp/{session_name}_valgrind.xml"
        local_output_file = f"{output_dir}/{session_name}_valgrind.xml"
        
        # Copy Valgrind output from container
        copy_cmd = f"docker cp {container_id}:{valgrind_internal_file} {local_output_file}"
        exit_code, stdout, stderr = device.execute_command(copy_cmd)
        
        if exit_code == 0:
            logger.info(f"✅ Valgrind output collected: {local_output_file}")
            
            # Check file size
            stat_cmd = f"ls -la {local_output_file}"
            exit_code, stdout, stderr = device.execute_command(stat_cmd)
            if exit_code == 0:
                logger.info(f"📊 Output file info: {stdout.strip()}")
        else:
            logger.error(f"❌ Failed to collect Valgrind output: {stderr}")
            
            # Try to find any valgrind files
            find_cmd = f"docker exec {container_id} find /tmp -name '*valgrind*' -type f"
            exit_code, stdout, stderr = device.execute_command(find_cmd)
            if exit_code == 0 and stdout.strip():
                logger.info(f"📁 Found Valgrind files in container: {stdout}")
        
        # Step 10: Restart netconfd normally
        logger.info("🔄 Step 10: Restarting netconfd normally...")
        
        if docker_manager.restart_netconfd_normally_in_container(container_id):
            logger.info("✅ netconfd restarted normally")
        else:
            logger.warning("⚠️ Failed to restart netconfd normally")
        
        # Step 11: Generate session summary
        logger.info("📋 Step 11: Generating session summary...")
        
        summary = {
            "session_id": session_name,
            "device_host": device_host,
            "container_id": container_id,
            "profiler": profiler,
            "profiling_duration": profiling_duration,
            "memory_limit": memory_limit,
            "original_memory_limit": original_memory_limit,
            "valgrind_pid": valgrind_pid,
            "existing_processes_killed": len(existing_processes),
            "output_file": local_output_file,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "completed"
        }
        
        summary_file = f"{output_dir}/{session_name}_summary.json"
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"📄 Session summary saved: {summary_file}")
        logger.info("🎉 Containerized memory test completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during containerized memory test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
        
    finally:
        # Cleanup: Restore original memory limit
        if docker_manager and original_memory_limit:
            logger.info(f"🔄 Cleanup: Restoring original memory limit: {original_memory_limit}")
            try:
                docker_manager.increase_container_memory(container_id, original_memory_limit)
                logger.info("✅ Memory limit restored")
            except Exception as e:
                logger.warning(f"⚠️ Failed to restore memory limit: {e}")
        
        # Disconnect from device
        if device:
            try:
                device.disconnect()
                logger.info("🔌 Disconnected from device")
            except Exception as e:
                logger.warning(f"⚠️ Error disconnecting: {e}")

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
    return run_containerized_memory_test(args.device_host, args.device_user, args.device_password or "",
                                         args.container_id, args.process_pid, args.memory_limit,
                                         args.profiler, args.session_name, args.profiling_duration,
                                         args.output_dir)

if __name__ == "__main__":
    sys.exit(main()) 