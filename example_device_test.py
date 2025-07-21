#!/usr/bin/env python3
"""
Example Device Memory Testing Script
Demonstrates how to use the device memory leak testing features
"""

import sys
from pathlib import Path
import time

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent))

from src.device.device_connector import DeviceConfig, DeviceConnector
from src.device.netconf_client import NetconfConfig, RpcOperation, NetconfClient
from src.device.memory_profiler import ProfilingConfig, MemoryProfiler
from src.device.integration_manager import IntegrationManager, TestConfig

def example_manual_testing():
    """Example of manual step-by-step testing"""
    print("🔧 MANUAL DEVICE MEMORY TESTING EXAMPLE")
    print("=" * 60)
    
    # Configure device connection
    device_config = DeviceConfig(
        hostname="192.168.1.100",  # Replace with your device IP
        port=22,
        username="admin",
        password="admin123",  # Replace with your credentials
        connection_type="ssh"
    )
    
    # Configure NETCONF connection
    netconf_config = NetconfConfig(
        host="192.168.1.100",  # Same as device or different NETCONF server
        port=830,
        username="admin",
        password="admin123"
    )
    
    print("Step 1: Testing device connection...")
    try:
        with DeviceConnector(device_config) as device:
            system_info = device.get_system_info()
            print(f"✅ Connected to: {system_info.get('hostname', 'unknown')}")
            
            # Find NETCONF processes
            processes = device.find_netconf_processes()
            if processes:
                print(f"✅ Found {len(processes)} NETCONF processes:")
                for proc in processes:
                    print(f"   PID {proc.pid}: {proc.name} ({proc.memory_usage}KB)")
            else:
                print("⚠️  No NETCONF processes found")
                return
            
            target_process = processes[0]  # Use first process
            
            print(f"\nStep 2: Starting memory profiling on PID {target_process.pid}...")
            profiler = MemoryProfiler(device)
            
            # Start Valgrind profiling
            session = profiler.start_valgrind_profiling(target_process.pid)
            if session:
                print(f"✅ Profiling started: {session.session_id}")
                
                print("\nStep 3: Executing NETCONF operations...")
                # Create some RPC operations
                rpc_ops = [
                    RpcOperation(
                        name="get_config_test",
                        xml_content="<get-config><source><running/></source></get-config>",
                        repeat_count=10,
                        delay_between_repeats=1.0
                    )
                ]
                
                # Note: For this example, we'll simulate NETCONF operations
                # In practice, you would use NetconfClient here
                print("   Simulating NETCONF operations...")
                time.sleep(10)  # Simulate some activity
                
                print("\nStep 4: Stopping profiling and collecting results...")
                profiler.stop_profiling_session(session.session_id)
                
                # Download results
                output_dir = Path("./example_results")
                output_dir.mkdir(exist_ok=True)
                
                local_file = profiler.download_session_logs(session.session_id, output_dir)
                if local_file:
                    print(f"✅ Results downloaded to: {local_file}")
                else:
                    print("❌ Failed to download results")
                
                # Cleanup
                profiler.cleanup_remote_files(session.session_id)
                print("✅ Remote files cleaned up")
            else:
                print("❌ Failed to start profiling")
                
    except Exception as e:
        print(f"❌ Manual testing failed: {e}")

def example_automated_testing():
    """Example of automated end-to-end testing"""
    print("\n🤖 AUTOMATED DEVICE MEMORY TESTING EXAMPLE")
    print("=" * 60)
    
    # Configure the complete test
    device_config = DeviceConfig(
        hostname="192.168.1.100",  # Replace with your device
        username="admin",
        password="admin123"
    )
    
    netconf_config = NetconfConfig(
        host="192.168.1.100",
        username="admin", 
        password="admin123"
    )
    
    profiling_config = ProfilingConfig(
        profiler_type="valgrind",
        session_timeout=1800  # 30 minutes
    )
    
    # Create RPC operations for testing
    rpc_operations = [
        RpcOperation(
            name="get_running_config",
            xml_content="<get-config><source><running/></source></get-config>",
            description="Get running configuration",
            repeat_count=15,
            delay_between_repeats=2.0
        ),
        RpcOperation(
            name="get_startup_config",
            xml_content="<get-config><source><startup/></source></get-config>",
            description="Get startup configuration", 
            repeat_count=5,
            delay_between_repeats=1.0
        ),
        RpcOperation(
            name="edit_config_test",
            xml_content="""
            <edit-config>
                <target><candidate/></target>
                <config>
                    <test-config xmlns="http://example.com/test">
                        <test-item>memory-test-value</test-item>
                    </test-config>
                </config>
            </edit-config>
            """,
            description="Test configuration edits",
            repeat_count=25,
            delay_between_repeats=0.5
        )
    ]
    
    # Create test configuration
    test_config = TestConfig(
        session_name="automated_memory_test",
        device_config=device_config,
        netconf_config=netconf_config,
        profiling_config=profiling_config,
        rpc_operations=rpc_operations,
        output_directory=Path("./automated_test_results"),
        cleanup_remote_files=True,
        auto_analyze=True,
        generate_reports=True
    )
    
    # Run the test
    manager = IntegrationManager()
    
    try:
        print("Starting automated test session...")
        session_id = manager.start_test_session(test_config)
        
        if session_id:
            session = manager.get_session_status(session_id)
            print(f"✅ Test completed successfully!")
            print(f"   Session ID: {session_id}")
            print(f"   Status: {session.status}")
            print(f"   Duration: {session.end_time - session.start_time}")
            
            if session.analysis_results:
                results = session.analysis_results
                print(f"\n📊 Memory Analysis Results:")
                print(f"   Total leaks found: {results['total_leaks']}")
                print(f"   Total bytes leaked: {results['total_bytes']:,}")
                print(f"   Severity breakdown: {results['by_severity']}")
            
            # Export summary
            summary_file = test_config.output_directory / f"{session_id}_summary.json"
            manager.export_session_summary(session_id, summary_file)
            print(f"   Summary exported to: {summary_file}")
            
        else:
            print("❌ Automated test failed")
            
    except Exception as e:
        print(f"❌ Automated testing failed: {e}")

def example_ci_integration():
    """Example showing how to integrate with CI/CD pipelines"""
    print("\n🔄 CI/CD INTEGRATION EXAMPLE")
    print("=" * 60)
    
    print("Example Jenkins Pipeline Script:")
    print("""
pipeline {
    agent any
    
    stages {
        stage('Deploy to Test Device') {
            steps {
                // Deploy your NETCONF application with ASan/Valgrind enabled
                sh 'deploy_to_device.sh ${DEVICE_IP}'
            }
        }
        
        stage('Memory Leak Testing') {
            steps {
                sh '''
                    python device_memory_tester.py \\
                        --device-host ${DEVICE_IP} \\
                        --device-user admin \\
                        --device-password ${DEVICE_PASSWORD} \\
                        --netconf-host ${DEVICE_IP} \\
                        --netconf-user admin \\
                        --netconf-password ${DEVICE_PASSWORD} \\
                        --profiler valgrind \\
                        --rpc-dir ./test_rpcs \\
                        --session-name build_${BUILD_NUMBER} \\
                        --output-dir ./memory_test_results \\
                        --log-level INFO
                '''
            }
        }
        
        stage('Analyze Results') {
            steps {
                script {
                    // Use memory_leak_analyzer for detailed analysis
                    sh '''
                        python memory_leak_analyzer_enhanced.py \\
                            --input ./memory_test_results/*_valgrind.xml \\
                            --cleanup \\
                            --impact-analysis \\
                            --trend-analysis \\
                            --version ${BUILD_NUMBER} \\
                            --ci-mode
                    '''
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'memory_test_results/**/*', fingerprint: true
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'memory_test_results',
                        reportFiles: '*_report.html',
                        reportName: 'Memory Leak Report'
                    ])
                }
            }
        }
    }
}
    """)

def example_usage_scenarios():
    """Show different usage scenarios"""
    print("\n💡 USAGE SCENARIOS")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "Development Testing",
            "description": "Quick memory check during development",
            "command": """
python device_memory_tester.py \\
    --device-host 192.168.1.100 \\
    --device-user dev \\
    --device-password dev123 \\
    --profiler asan \\
    --rpc-dir ./quick_test_rpcs \\
    --session-name dev_test
            """
        },
        {
            "name": "Nightly Regression Testing",
            "description": "Comprehensive nightly memory leak testing",
            "command": """
python device_memory_tester.py \\
    --device-host test-device.company.com \\
    --device-user testuser \\
    --device-key ~/.ssh/test_key \\
    --profiler valgrind \\
    --profiler-timeout 7200 \\
    --rpc-dir ./comprehensive_test_rpcs \\
    --session-name nightly_regression \\
    --output-dir ./nightly_results
            """
        },
        {
            "name": "Release Validation",
            "description": "Pre-release memory validation",
            "command": """
python device_memory_tester.py \\
    --device-host release-validation.company.com \\
    --device-user validator \\
    --device-password $VALIDATOR_PASSWORD \\
    --profiler valgrind \\
    --rpc-dir ./release_validation_rpcs \\
    --session-name release_v2.1.0 \\
    --output-dir ./release_validation
            """
        },
        {
            "name": "Performance Testing",
            "description": "Memory performance under load",
            "command": """
python device_memory_tester.py \\
    --device-host perf-test-device \\
    --device-user perftest \\
    --device-password perftest123 \\
    --profiler asan \\
    --rpc-dir ./performance_test_rpcs \\
    --session-name performance_test \\
    --no-cleanup  # Keep files for detailed analysis
            """
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🎯 {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Command:")
        print(scenario['command'])

def main():
    print("🚀 DEVICE MEMORY LEAK TESTING EXAMPLES")
    print("=" * 80)
    print("This script demonstrates the device memory testing capabilities.")
    print("Note: These examples use placeholder IP addresses and credentials.")
    print("Replace them with your actual device information.")
    print("=" * 80)
    
    # Show different examples
    example_usage_scenarios()
    print("\n" + "=" * 80)
    print("To actually run tests, use the device_memory_tester.py tool!")
    print("Example: python device_memory_tester.py --help")

if __name__ == "__main__":
    main() 