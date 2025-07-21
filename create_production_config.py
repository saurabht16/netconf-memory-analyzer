#!/usr/bin/env python3
"""
Production Configuration Generator
Create configuration files for real device testing
"""

import yaml
import argparse
from pathlib import Path

def create_simple_config(device_ip: str, username: str, password: str, container_id: str, output_file: str):
    """Create a simple single-device configuration"""
    
    config = {
        'devices': {
            'my_device': {
                'connection': {
                    'hostname': device_ip,
                    'port': 22,
                    'username': username,
                    'password': password
                },
                'test_scenarios': [
                    {
                        'name': 'ui_memory_test',
                        'container_id': container_id,
                        'memory_limit': '5g',
                        'profiler': 'valgrind',
                        'profiling_duration': 60,
                        'restore_memory': True,
                        'output': {
                            'session_name': 'production_test',
                            'output_dir': 'results/production_device'
                        }
                    }
                ]
            }
        },
        'global_config': {
            'max_parallel_devices': 1,
            'log_level': 'INFO',
            'cleanup_on_failure': True,
            'consolidated_report': True,
            'consolidated_report_dir': 'results/consolidated'
        }
    }
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)
    
    print(f"✅ Created configuration: {output_path}")
    return output_path

def create_multi_device_config(devices: list, output_file: str):
    """Create a multi-device configuration"""
    
    device_configs = {}
    
    for i, device_info in enumerate(devices):
        device_name = f"device_{i+1}"
        device_configs[device_name] = {
            'connection': {
                'hostname': device_info['ip'],
                'port': device_info.get('port', 22),
                'username': device_info['username'],
                'password': device_info['password']
            },
            'test_scenarios': [
                {
                    'name': f"container_test_{j+1}",
                    'container_id': container['id'],
                    'memory_limit': container.get('memory', '5g'),
                    'profiler': 'valgrind',
                    'profiling_duration': container.get('duration', 120),
                    'restore_memory': True,
                    'output': {
                        'session_name': f"{device_name}_{container['id']}_test",
                        'output_dir': f"results/{device_name}"
                    }
                }
                for j, container in enumerate(device_info.get('containers', [{'id': 'netconf-ui'}]))
            ]
        }
    
    config = {
        'devices': device_configs,
        'global_config': {
            'max_parallel_devices': min(3, len(devices)),
            'max_parallel_tests_per_device': 2,
            'connection_timeout': 30,
            'test_timeout': 3600,
            'log_level': 'INFO',
            'log_file': 'logs/parallel_device_testing.log',
            'consolidated_report': True,
            'consolidated_report_dir': 'results/consolidated',
            'cleanup_on_failure': True
        }
    }
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)
    
    print(f"✅ Created multi-device configuration: {output_path}")
    return output_path

def interactive_config_creator():
    """Interactive configuration creator"""
    print("🔧 INTERACTIVE DEVICE CONFIGURATION CREATOR")
    print("=" * 60)
    
    devices = []
    
    while True:
        print(f"\n📱 Device {len(devices) + 1} Configuration:")
        print("-" * 40)
        
        device_ip = input("Device IP/Hostname: ").strip()
        if not device_ip:
            break
            
        username = input("SSH Username: ").strip()
        password = input("SSH Password: ").strip()
        
        # Container configuration
        containers = []
        print("\n🐳 Container Configuration:")
        
        while True:
            container_id = input(f"Container {len(containers) + 1} ID (or Enter to finish): ").strip()
            if not container_id:
                break
                
            memory = input(f"Memory limit for {container_id} (default: 5g): ").strip() or "5g"
            duration = input(f"Test duration for {container_id} (default: 120s): ").strip()
            duration = int(duration) if duration.isdigit() else 120
            
            containers.append({
                'id': container_id,
                'memory': memory,
                'duration': duration
            })
        
        if not containers:
            containers = [{'id': 'netconf-ui'}]  # Default container
        
        devices.append({
            'ip': device_ip,
            'username': username,
            'password': password,
            'containers': containers
        })
        
        more = input("\nAdd another device? (y/N): ").strip().lower()
        if more != 'y':
            break
    
    if devices:
        output_file = input("\nOutput file (default: config/my_production_devices.yaml): ").strip()
        output_file = output_file or "config/my_production_devices.yaml"
        
        if len(devices) == 1:
            create_simple_config(
                devices[0]['ip'], 
                devices[0]['username'], 
                devices[0]['password'],
                devices[0]['containers'][0]['id'],
                output_file
            )
        else:
            create_multi_device_config(devices, output_file)
        
        print(f"\n🎉 Configuration created! To run tests:")
        print(f"   python parallel_device_tester.py --config {output_file} --list")
        print(f"   python parallel_device_tester.py --config {output_file} --discover")
        print(f"   python parallel_device_tester.py --config {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Production Configuration Generator')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Simple config command
    simple_parser = subparsers.add_parser('simple', help='Create simple single-device config')
    simple_parser.add_argument('--device-ip', required=True, help='Device IP address')
    simple_parser.add_argument('--username', required=True, help='SSH username')
    simple_parser.add_argument('--password', required=True, help='SSH password')
    simple_parser.add_argument('--container-id', required=True, help='Container ID to test')
    simple_parser.add_argument('--output', default='config/production_config.yaml', help='Output file')
    
    # Interactive command
    subparsers.add_parser('interactive', help='Interactive configuration creator')
    
    args = parser.parse_args()
    
    if args.command == 'simple':
        create_simple_config(
            args.device_ip,
            args.username, 
            args.password,
            args.container_id,
            args.output
        )
        
        print(f"\n💡 Next steps:")
        print(f"   1. List devices: python parallel_device_tester.py --config {args.output} --list")
        print(f"   2. Discover containers: python parallel_device_tester.py --config {args.output} --discover")
        print(f"   3. Run test: python parallel_device_tester.py --config {args.output}")
        
    elif args.command == 'interactive':
        interactive_config_creator()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 