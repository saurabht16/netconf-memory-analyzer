#!/usr/bin/env python3
"""
Device Memory Leak Tester
Complete solution for testing memory leaks in NETCONF processes on remote devices
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List
import time
import json

from src.device.device_connector import DeviceConfig
from src.device.netconf_client import NetconfConfig, RpcOperation
from src.device.memory_profiler import ProfilingConfig
from src.device.integration_manager import IntegrationManager, TestConfig

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('device_memory_tester.log')
        ]
    )

def load_rpc_operations(rpc_dir: Path) -> List[RpcOperation]:
    """Load RPC operations from directory or create default ones"""
    operations = []
    
    if rpc_dir and rpc_dir.exists():
        # Load from directory
        from src.device.netconf_client import NetconfClient
        dummy_config = NetconfConfig(host="localhost")  # Not used for loading
        client = NetconfClient(dummy_config)
        operations = client.load_rpc_directory(rpc_dir)
    else:
        # Create some default RPC operations for testing
        operations = [
            RpcOperation(
                name="get_config_startup",
                xml_content="""
<get-config>
    <source>
        <startup/>
    </source>
</get-config>
                """,
                description="Get startup configuration",
                repeat_count=5,
                delay_between_repeats=1.0
            ),
            RpcOperation(
                name="get_config_running",
                xml_content="""
<get-config>
    <source>
        <running/>
    </source>
</get-config>
                """,
                description="Get running configuration",
                repeat_count=10,
                delay_between_repeats=0.5
            ),
            RpcOperation(
                name="get_capabilities",
                xml_content="""
<get>
    <filter type="xpath" select="/netconf-state/capabilities"/>
</get>
                """,
                description="Get NETCONF capabilities",
                repeat_count=3
            ),
            RpcOperation(
                name="edit_config_test",
                xml_content="""
<edit-config>
    <target>
        <candidate/>
    </target>
    <config>
        <test-config xmlns="http://example.com/test">
            <test-value>memory-leak-test</test-value>
        </test-config>
    </config>
</edit-config>
                """,
                description="Test configuration edit",
                repeat_count=20,
                delay_between_repeats=0.2
            )
        ]
    
    return operations

def create_sample_rpc_directory(output_dir: Path):
    """Create sample RPC files for testing"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sample_rpcs = {
        "get_config.xml": """<?xml version="1.0" encoding="UTF-8"?>
<get-config>
    <source>
        <running/>
    </source>
</get-config>""",
        
        "get_state.xml": """<?xml version="1.0" encoding="UTF-8"?>
<get>
    <filter type="subtree">
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name/>
                <oper-status/>
            </interface>
        </interfaces>
    </filter>
</get>""",
        
        "edit_config.xml": """<?xml version="1.0" encoding="UTF-8"?>
<edit-config>
    <target>
        <candidate/>
    </target>
    <config>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name>test-interface</name>
                <description>Memory leak test interface</description>
                <enabled>true</enabled>
            </interface>
        </interfaces>
    </config>
</edit-config>""",
        
        "lock_unlock.xml": """<?xml version="1.0" encoding="UTF-8"?>
<lock>
    <target>
        <candidate/>
    </target>
</lock>"""
    }
    
    for filename, content in sample_rpcs.items():
        with open(output_dir / filename, 'w') as f:
            f.write(content)
    
    print(f"Created sample RPC files in {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='Device Memory Leak Tester for NETCONF processes')
    
    # Device connection options
    parser.add_argument('--device-host', required=True, help='Device hostname or IP')
    parser.add_argument('--device-port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--device-user', required=True, help='SSH username')
    parser.add_argument('--device-password', help='SSH password')
    parser.add_argument('--device-key', help='SSH private key file')
    
    # NETCONF connection options
    parser.add_argument('--netconf-host', help='NETCONF server host (default: same as device)')
    parser.add_argument('--netconf-port', type=int, default=830, help='NETCONF port (default: 830)')
    parser.add_argument('--netconf-user', help='NETCONF username (default: same as device)')
    parser.add_argument('--netconf-password', help='NETCONF password (default: same as device)')
    
    # Profiling options
    parser.add_argument('--profiler', choices=['valgrind', 'asan'], default='valgrind',
                       help='Memory profiler to use (default: valgrind)')
    parser.add_argument('--profiler-timeout', type=int, default=3600,
                       help='Profiling timeout in seconds (default: 3600)')
    
    # Test options
    parser.add_argument('--rpc-dir', type=Path, help='Directory containing RPC XML files')
    parser.add_argument('--session-name', default='device_memory_test',
                       help='Test session name (default: device_memory_test)')
    parser.add_argument('--output-dir', type=Path, default=Path('./memory_test_results'),
                       help='Output directory for results (default: ./memory_test_results)')
    
    # Utility options
    parser.add_argument('--create-sample-rpcs', type=Path, 
                       help='Create sample RPC files in specified directory')
    parser.add_argument('--list-processes', action='store_true',
                       help='List NETCONF processes on device and exit')
    parser.add_argument('--test-connection', action='store_true',
                       help='Test device connection and exit')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level (default: INFO)')
    
    # Analysis options
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Keep remote files after testing')
    parser.add_argument('--no-analysis', action='store_true',
                       help='Skip automatic analysis')
    parser.add_argument('--no-reports', action='store_true',
                       help='Skip report generation')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Handle utility commands
    if args.create_sample_rpcs:
        create_sample_rpc_directory(args.create_sample_rpcs)
        return 0
    
    # Create device configuration
    device_config = DeviceConfig(
        hostname=args.device_host,
        port=args.device_port,
        username=args.device_user,
        password=args.device_password or "",
        key_file=args.device_key or ""
    )
    
    # Test connection if requested
    if args.test_connection:
        logger.info("Testing device connection...")
        try:
            from src.device.device_connector import DeviceConnector
            with DeviceConnector(device_config) as device:
                system_info = device.get_system_info()
                print("✅ Connection successful!")
                print(f"Device: {system_info.get('hostname', 'unknown')}")
                print(f"OS: {system_info.get('os_version', 'unknown')}")
                print(f"Uptime: {system_info.get('uptime', 'unknown')}")
                return 0
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return 1
    
    # List processes if requested
    if args.list_processes:
        logger.info("Listing NETCONF processes...")
        try:
            from src.device.device_connector import DeviceConnector
            with DeviceConnector(device_config) as device:
                processes = device.find_netconf_processes()
                if processes:
                    print("Found NETCONF processes:")
                    for proc in processes:
                        print(f"  PID {proc.pid}: {proc.name} ({proc.memory_usage}KB)")
                        print(f"    Command: {proc.command}")
                else:
                    print("No NETCONF processes found")
                return 0
        except Exception as e:
            print(f"❌ Failed to list processes: {e}")
            return 1
    
    # Create NETCONF configuration
    netconf_config = NetconfConfig(
        host=args.netconf_host or args.device_host,
        port=args.netconf_port,
        username=args.netconf_user or args.device_user,
        password=args.netconf_password or args.device_password or ""
    )
    
    # Create profiling configuration
    profiling_config = ProfilingConfig(
        profiler_type=args.profiler,
        session_timeout=args.profiler_timeout
    )
    
    # Load RPC operations
    logger.info("Loading RPC operations...")
    rpc_operations = load_rpc_operations(args.rpc_dir)
    
    if not rpc_operations:
        logger.error("No RPC operations loaded. Use --create-sample-rpcs to create sample files.")
        return 1
    
    logger.info(f"Loaded {len(rpc_operations)} RPC operations")
    
    # Create test configuration
    test_config = TestConfig(
        session_name=args.session_name,
        device_config=device_config,
        netconf_config=netconf_config,
        profiling_config=profiling_config,
        rpc_operations=rpc_operations,
        output_directory=args.output_dir,
        cleanup_remote_files=not args.no_cleanup,
        auto_analyze=not args.no_analysis,
        generate_reports=not args.no_reports
    )
    
    # Start the test
    logger.info("🚀 Starting device memory leak testing...")
    logger.info(f"Device: {args.device_host}")
    logger.info(f"Profiler: {args.profiler}")
    logger.info(f"RPC operations: {len(rpc_operations)}")
    logger.info(f"Output directory: {args.output_dir}")
    
    # Initialize integration manager
    manager = IntegrationManager()
    
    try:
        # Start test session
        session_id = manager.start_test_session(test_config)
        
        if session_id:
            session = manager.get_session_status(session_id)
            print("\n🎉 Test completed successfully!")
            print(f"Session ID: {session_id}")
            print(f"Status: {session.status}")
            print(f"Duration: {session.end_time - session.start_time}")
            
            if session.analysis_results:
                results = session.analysis_results
                print(f"\n📊 Analysis Results:")
                print(f"  Total leaks: {results['total_leaks']}")
                print(f"  Total bytes: {results['total_bytes']:,}")
                print(f"  By severity: {results['by_severity']}")
            
            if session.local_log_path:
                print(f"\n📁 Files generated:")
                print(f"  Log file: {session.local_log_path}")
                
                # List other generated files
                for file_path in args.output_dir.glob(f"{session_id}*"):
                    if file_path != session.local_log_path:
                        print(f"  Report: {file_path}")
            
            # Export session summary
            summary_file = args.output_dir / f"{session_id}_summary.json"
            manager.export_session_summary(session_id, summary_file)
            print(f"  Summary: {summary_file}")
            
            return 0
        else:
            print("❌ Test failed to complete")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        print("\n⚠️  Test interrupted")
        return 1
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 