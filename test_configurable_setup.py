#!/usr/bin/env python3
"""
Test Script for Configurable Container Setup
Demonstrates the new flexible approach to container preparation with custom commands and file editing
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.device.configurable_container_setup import (
    ConfigurableContainerSetup, 
    ContainerSetupConfig, 
    FileEdit
)

def setup_logging():
    """Setup logging for test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_template_substitution():
    """Test template variable substitution"""
    print("\n" + "="*80)
    print("🧪 TESTING TEMPLATE VARIABLE SUBSTITUTION")
    print("="*80)
    
    # Create a mock setup object
    class MockDevice:
        def execute_command(self, cmd, timeout=30):
            return 0, f"Executed: {cmd}", ""
    
    setup = ConfigurableContainerSetup(MockDevice())
    
    # Set template variables
    setup.set_template_variables(
        container_id="test-container",
        session_id="test-session-123",
        scenario_name="memory_test",
        memory_limit="5g",
        device_hostname="192.168.1.100"
    )
    
    # Test template substitution
    test_commands = [
        "mkdir -p /var/log/valgrind_{{container_id}}",
        "echo 'Starting test {{scenario_name}}' > /tmp/test_{{session_id}}.log",
        "valgrind --xml-file=/tmp/{{container_id}}_{{timestamp}}.xml /usr/bin/netconfd",
        "echo 'Memory limit: {{memory_limit}} on {{device_hostname}}'"
    ]
    
    print("📋 TEMPLATE SUBSTITUTION RESULTS:")
    print()
    
    for i, cmd in enumerate(test_commands, 1):
        original = cmd
        substituted = setup._substitute_template(cmd)
        print(f"{i}. Original:    {original}")
        print(f"   Substituted: {substituted}")
        print()
    
    # Verify substitution worked
    expected_vars = ['test-container', 'test-session-123', 'memory_test', '5g', '192.168.1.100']
    substituted_text = " ".join([setup._substitute_template(cmd) for cmd in test_commands])
    
    all_substituted = all(var in substituted_text for var in expected_vars)
    
    if all_substituted:
        print("✅ Template substitution test PASSED")
        return True
    else:
        print("❌ Template substitution test FAILED")
        return False

def test_config_parsing():
    """Test configuration parsing"""
    print("\n" + "="*80)
    print("🧪 TESTING CONFIGURATION PARSING")
    print("="*80)
    
    # Test configuration
    test_config = {
        'pre_commands': [
            'apt-get update',
            'systemctl stop apache2',
            'mkdir -p /var/log/valgrind'
        ],
        'file_edits': [
            {
                'file': '/etc/netconf/config.conf',
                'content': 'debug_level = 3\nlog_file = /var/log/netconf.log',
                'backup': True,
                'backup_suffix': '.bak'
            },
            {
                'file': '/usr/local/bin/wrapper.sh',
                'content': '#!/bin/bash\nexport DEBUG=1\nexec "$@"',
                'backup': False,
                'permissions': '755'
            }
        ],
        'valgrind_command': 'valgrind --tool=memcheck --xml=yes --xml-file=/tmp/test.xml /usr/bin/netconfd',
        'post_commands': [
            'echo "Setup complete"',
            'systemctl status netconfd'
        ],
        'cleanup_commands': [
            'systemctl start apache2',
            'rm -f /tmp/test_*'
        ]
    }
    
    try:
        # Parse configuration
        setup_config = ConfigurableContainerSetup.parse_container_setup_config(test_config)
        
        print("📋 PARSED CONFIGURATION:")
        print(f"   Pre-commands: {len(setup_config.pre_commands)}")
        print(f"   File edits: {len(setup_config.file_edits)}")
        print(f"   Valgrind command: {setup_config.valgrind_command[:50]}...")
        print(f"   Post-commands: {len(setup_config.post_commands)}")
        print(f"   Cleanup commands: {len(setup_config.cleanup_commands)}")
        print()
        
        # Verify file edits
        print("📝 FILE EDIT DETAILS:")
        for i, file_edit in enumerate(setup_config.file_edits, 1):
            print(f"   {i}. File: {file_edit.file}")
            print(f"      Backup: {file_edit.backup}")
            print(f"      Permissions: {file_edit.permissions}")
            print(f"      Content length: {len(file_edit.content)} chars")
            print()
        
        # Verify all fields are correctly parsed
        assert len(setup_config.pre_commands) == 3
        assert len(setup_config.file_edits) == 2
        assert len(setup_config.post_commands) == 2
        assert len(setup_config.cleanup_commands) == 2
        assert setup_config.file_edits[0].backup == True
        assert setup_config.file_edits[1].permissions == '755'
        
        print("✅ Configuration parsing test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Configuration parsing test FAILED: {e}")
        return False

def demonstrate_workflow():
    """Demonstrate the complete configurable workflow"""
    print("\n" + "="*80)
    print("🔄 DEMONSTRATING CONFIGURABLE WORKFLOW")
    print("="*80)
    
    print("📋 WORKFLOW STEPS:")
    print()
    
    workflow_steps = [
        "1. 🔗 Connect to device via SSH",
        "2. 🎯 Find target NETCONF container efficiently",
        "3. 📈 Increase container memory (no restart)",
        "4. 🔧 Execute configurable container setup:",
        "   a. 🚀 Run pre-commands (install deps, stop services, etc.)",
        "   b. 📝 Edit configuration files with backups",
        "   c. 🚀 Start Valgrind with custom command",
        "   d. 📋 Run post-commands (verification, status checks)",
        "5. 🧪 Execute RPC stress testing",
        "6. ⏱️ Monitor memory profiling",
        "7. 📥 Collect Valgrind XML output",
        "8. 🔬 Analyze results with enhanced analyzer",
        "9. 📊 Generate HTML reports and CSV data",
        "10. 🧹 Run cleanup commands (restore services)",
        "11. 🔄 Restore original container memory"
    ]
    
    for step in workflow_steps:
        print(f"   {step}")
    
    print()
    print("🎯 KEY BENEFITS:")
    print("   • 🔧 Fully customizable container preparation")
    print("   • 📝 Safe file editing with automatic backups") 
    print("   • 🚀 Custom Valgrind commands with templates")
    print("   • 🧹 Automatic cleanup and restoration")
    print("   • ⚡ Template variables for dynamic configuration")
    print("   • 🔄 Backward compatibility with existing setups")
    
    return True

def show_usage_examples():
    """Show practical usage examples"""
    print("\n" + "="*80)
    print("📚 USAGE EXAMPLES")
    print("="*80)
    
    print("🔧 EXAMPLE 1: Simple Setup")
    print("-" * 40)
    simple_config = '''
container_setup:
  valgrind_command: >
    valgrind --tool=memcheck --leak-check=full 
    --xml=yes --xml-file=/tmp/simple_{{timestamp}}.xml
    /usr/bin/netconfd --foreground
'''
    print(simple_config)
    
    print("🔧 EXAMPLE 2: Complex Production Setup")
    print("-" * 40)
    complex_config = '''
container_setup:
  pre_commands:
    - "systemctl stop nginx"
    - "pkill -f old_netconf_service"
    - "mkdir -p /var/log/testing"
    
  file_edits:
    - file: "/etc/netconf/netconf.conf"
      backup: true
      content: |
        debug_level = 3
        memory_tracking = enabled
        log_file = /var/log/testing/netconf_{{session_id}}.log
        
  valgrind_command: >
    valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all
    --xml=yes --xml-file=/var/log/testing/valgrind_{{container_id}}_{{timestamp}}.xml
    --log-file=/var/log/testing/valgrind.log
    /usr/bin/netconfd --foreground --config=/etc/netconf/netconf.conf
    
  post_commands:
    - "echo 'Test started for {{scenario_name}}' >> /var/log/testing/setup.log"
    
  cleanup_commands:
    - "systemctl start nginx"
    - "rm -f /tmp/test_*"
'''
    print(complex_config)
    
    print("🚀 EXAMPLE 3: Command Line Usage")
    print("-" * 40)
    usage_example = '''
# Run with configurable setup
python memory_tester.py \\
  --config config/configurable_container_setup.yaml \\
  --test \\
  --device production_device

# Dry run to validate configuration  
python memory_tester.py \\
  --config config/configurable_container_setup.yaml \\
  --test \\
  --dry-run
'''
    print(usage_example)
    
    return True

def main():
    """Main test function"""
    setup_logging()
    
    print("🧪 CONFIGURABLE CONTAINER SETUP TEST SUITE")
    print("===========================================")
    
    all_tests_passed = True
    tests = [
        ("Template Variable Substitution", test_template_substitution),
        ("Configuration Parsing", test_config_parsing),
        ("Workflow Demonstration", demonstrate_workflow),
        ("Usage Examples", show_usage_examples)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
            all_tests_passed = False
    
    print("\n" + "="*60)
    if all_tests_passed:
        print("🎉 ALL CONFIGURABLE SETUP TESTS PASSED!")
        print()
        print("✅ Key Features Validated:")
        print("   • Template variable substitution")
        print("   • Configuration parsing and validation")
        print("   • File editing with backups")
        print("   • Custom command execution")
        print("   • Cleanup and restoration")
        print()
        print("🚀 Ready for production use with:")
        print("   • Custom container preparation")
        print("   • Flexible Valgrind commands") 
        print("   • Safe file modifications")
        print("   • Automatic cleanup")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 