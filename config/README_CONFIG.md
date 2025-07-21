# Device Configuration Guide

This guide explains how to configure and run parallel memory testing across multiple devices using configuration files.

## Quick Start

1. **Copy and customize a configuration file:**
   ```bash
   cp config/simple_device_config.yaml config/my_devices.yaml
   # Edit config/my_devices.yaml with your device details
   ```

2. **List your configured devices:**
   ```bash
   python parallel_device_tester.py --config config/my_devices.yaml --list
   ```

3. **Discover containers on your devices:**
   ```bash
   python parallel_device_tester.py --config config/my_devices.yaml --discover
   ```

4. **Run tests on all devices in parallel:**
   ```bash
   python parallel_device_tester.py --config config/my_devices.yaml
   ```

## Configuration File Structure

### Basic Device Configuration

```yaml
devices:
  my_device:                          # Device identifier (choose any name)
    connection:
      hostname: "192.168.1.100"       # Required: Device IP or hostname
      port: 22                        # Optional: SSH port (default: 22)
      username: "admin"               # Required: SSH username
      password: "admin123"            # Required: SSH password OR use key_file
      # key_file: "~/.ssh/device_key" # Alternative: SSH private key file
    
    test_scenarios:                   # List of tests to run on this device
      - name: "ui_container_test"     # Test identifier
        container_id: "netconf-ui"    # Container name or ID to test
        process_pid: 1                # Process PID (optional - auto-discovered)
        memory_limit: "5g"            # Memory to allocate to container
        profiler: "valgrind"          # Profiler type: "valgrind" or "asan"
        profiling_duration: 120       # Test duration in seconds
        restore_memory: true          # Restore original memory after test
        
        # Optional: NETCONF stress testing
        netconf:
          host: "192.168.1.100"       # NETCONF server (default: same as device)
          port: 830                   # NETCONF port
          username: "admin"           # NETCONF username
          password: "admin123"        # NETCONF password
          rpc_dir: "test_data/sample_rpcs"  # Directory with RPC XML files
        
        # Optional: Output configuration
        output:
          session_name: "my_test"     # Test session name
          output_dir: "results/my_device"  # Results directory
```

### Multiple Devices Example

```yaml
devices:
  # Production Device 1
  prod_device_1:
    connection:
      hostname: "192.168.1.100"
      username: "admin"
      password: "prod_password"
    test_scenarios:
      - name: "ui_memory_test"
        container_id: "netconf-ui"
        memory_limit: "5g"
        profiling_duration: 300

  # Production Device 2  
  prod_device_2:
    connection:
      hostname: "192.168.1.101"
      username: "admin"
      password: "prod_password"
    test_scenarios:
      - name: "backend_test"
        container_id: "netconf-backend"
        memory_limit: "4g"
        profiling_duration: 180

# Global settings
global_config:
  max_parallel_devices: 2            # Test 2 devices simultaneously
  max_parallel_tests_per_device: 1   # 1 test per device at a time
  log_level: "INFO"
  cleanup_on_failure: true
```

## Usage Examples

### Test Single Device
```bash
python parallel_device_tester.py --config config/my_devices.yaml --device my_device
```

### Test Single Scenario
```bash
python parallel_device_tester.py --config config/my_devices.yaml --device my_device --scenario ui_memory_test
```

### Dry Run (Show What Would Execute)
```bash
python parallel_device_tester.py --config config/my_devices.yaml --dry-run
```

### Discovery Only
```bash
python parallel_device_tester.py --config config/my_devices.yaml --discover
```

## Configuration Parameters

### Device Connection
| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `hostname` | Yes | Device IP or hostname | `"192.168.1.100"` |
| `port` | No | SSH port (default: 22) | `22` |
| `username` | Yes | SSH username | `"admin"` |
| `password` | No* | SSH password | `"admin123"` |
| `key_file` | No* | SSH private key file | `"~/.ssh/device_key"` |

*Either `password` or `key_file` is required.

### Test Scenario Options
| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `name` | Yes | Test scenario name | - |
| `container_id` | Yes | Container name or ID | - |
| `process_pid` | No | Process PID to profile | Auto-discover |
| `memory_limit` | No | Container memory limit | `"5g"` |
| `profiler` | No | Profiler type | `"valgrind"` |
| `profiling_duration` | No | Test duration (seconds) | `60` |
| `restore_memory` | No | Restore memory after test | `true` |

### Global Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_parallel_devices` | Max devices to test simultaneously | `3` |
| `max_parallel_tests_per_device` | Max tests per device | `2` |
| `connection_timeout` | SSH connection timeout | `30` |
| `test_timeout` | Max test duration | `3600` |
| `log_level` | Logging level | `"INFO"` |
| `cleanup_on_failure` | Clean up on test failure | `true` |

## Output Structure

Tests generate results in the following structure:
```
results/
├── device1/                    # Per-device results
│   ├── session_logs.xml       # Valgrind/ASan logs
│   └── session_summary.json   # Test metadata
├── device2/
│   └── ...
└── consolidated/               # Overall results
    └── consolidated_report_20250720_143022.json
```

## Advanced Features

### Auto-Discovery
If you don't specify `process_pid`, the tool will automatically discover and use the first NETCONF process in the container.

### Multiple Test Scenarios
You can define multiple test scenarios per device to test different containers or configurations:

```yaml
devices:
  my_device:
    connection:
      hostname: "192.168.1.100"
      username: "admin"
      password: "password"
    test_scenarios:
      - name: "test_ui_container"
        container_id: "netconf-ui"
        memory_limit: "5g"
      - name: "test_backend_container"  
        container_id: "netconf-backend"
        memory_limit: "4g"
      - name: "test_datastore"
        container_id: "datastore"
        memory_limit: "3g"
```

### Parallel Execution Control
Control how many devices and tests run simultaneously:

```yaml
global_config:
  max_parallel_devices: 2        # Test 2 devices at once
  max_parallel_tests_per_device: 1  # 1 test per device at a time
```

This is useful for managing resource usage and avoiding overwhelming your devices.

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check hostname, username, password in config
   - Verify SSH access to device
   - Check if device is reachable

2. **Container Not Found**
   - Run discovery to see available containers
   - Check container name/ID in configuration
   - Verify container is running

3. **Process Not Found**
   - Remove `process_pid` to enable auto-discovery
   - Run discovery to see processes in container
   - Check if target process is running

4. **Memory Increase Failed**
   - Check if user has Docker privileges
   - Verify container can be stopped/restarted
   - Check if memory limit is valid

### Debug Mode
For troubleshooting, set log level to DEBUG:

```yaml
global_config:
  log_level: "DEBUG"
```

This provides detailed logging of all operations.

## Examples

See the provided example configuration files:
- `config/simple_device_config.yaml` - Basic single device setup
- `config/device_configs.yaml` - Advanced multi-device configuration 