# Device Memory Leak Testing for NETCONF Applications

This advanced feature allows you to **attach memory profilers to NETCONF processes running on remote devices**, execute RPC operations to trigger memory usage, and automatically analyze the results.

## 🚀 **Quick Start**

### 1. Create Sample RPC Files
```bash
python device_memory_tester.py --create-sample-rpcs ./my_rpcs
```

### 2. Test Device Connection
```bash
python device_memory_tester.py \
    --device-host 192.168.1.100 \
    --device-user admin \
    --device-password admin123 \
    --test-connection
```

### 3. List NETCONF Processes
```bash
python device_memory_tester.py \
    --device-host 192.168.1.100 \
    --device-user admin \
    --device-password admin123 \
    --list-processes
```

### 4. Run Complete Memory Test
```bash
python device_memory_tester.py \
    --device-host 192.168.1.100 \
    --device-user admin \
    --device-password admin123 \
    --profiler valgrind \
    --rpc-dir ./my_rpcs \
    --session-name my_test \
    --output-dir ./results
```

## 📋 **Prerequisites**

### Device Requirements
- **SSH access** to the target device
- **NETCONF server** running on the device
- **Valgrind and/or AddressSanitizer** installed on device
- NETCONF application **built with debugging symbols**
- Sufficient **disk space** for profiling logs

### Host Requirements
- Python 3.8+ with `paramiko` for SSH connections
- Network connectivity to device (SSH port 22, NETCONF port 830)

### Application Build Requirements
For best results, build your NETCONF application with:

**Valgrind Support:**
```bash
gcc -g -O0 -DDEBUG your_netconf_app.c -o netconf_app
```

**AddressSanitizer Support:**
```bash
gcc -fsanitize=address -fno-omit-frame-pointer -g -O1 your_netconf_app.c -o netconf_app
```

## 🔧 **Configuration Options**

### Device Connection
```bash
--device-host HOSTNAME      # Device IP or hostname (required)
--device-port PORT          # SSH port (default: 22)
--device-user USERNAME      # SSH username (required)
--device-password PASSWORD  # SSH password
--device-key PATH           # SSH private key file
```

### NETCONF Connection
```bash
--netconf-host HOSTNAME     # NETCONF server (default: same as device)
--netconf-port PORT         # NETCONF port (default: 830)
--netconf-user USERNAME     # NETCONF username (default: same as device)
--netconf-password PASSWORD # NETCONF password (default: same as device)
```

### Memory Profiling
```bash
--profiler {valgrind,asan}  # Profiler type (default: valgrind)
--profiler-timeout SECONDS # Timeout in seconds (default: 3600)
```

### Test Configuration
```bash
--rpc-dir DIRECTORY         # Directory with RPC XML files
--session-name NAME         # Test session name
--output-dir DIRECTORY      # Results output directory
--no-cleanup               # Keep remote files
--no-analysis              # Skip analysis
--no-reports               # Skip report generation
```

## 📁 **RPC File Format**

Create XML files for your NETCONF operations:

**get_config.xml:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<get-config>
    <source>
        <running/>
    </source>
</get-config>
```

**edit_config.xml:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<edit-config>
    <target>
        <candidate/>
    </target>
    <config>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name>test-interface</name>
                <description>Memory test interface</description>
                <enabled>true</enabled>
            </interface>
        </interfaces>
    </config>
</edit-config>
```

## 🔄 **Complete Workflow**

### 1. **Device Connection**
- Establishes SSH connection to device
- Validates credentials and connectivity
- Gathers system information

### 2. **Process Discovery**
- Scans for NETCONF processes (netconfd, confd, etc.)
- Lists running processes with memory usage
- Selects target process for profiling

### 3. **Memory Profiling Setup**
- **Valgrind**: Attaches to process with memcheck
- **AddressSanitizer**: Configures environment variables
- Creates remote output directories

### 4. **NETCONF Operations**
- Loads RPC operations from XML files
- Executes operations with configurable repetition
- Measures timing and success rates

### 5. **Log Collection**
- Stops profiling session gracefully
- Downloads logs from device to host
- Optionally cleans up remote files

### 6. **Analysis & Reporting**
- Parses Valgrind XML or ASan logs
- Applies cleanup filters
- Generates HTML and CSV reports
- Provides actionable recommendations

## 📊 **Output Files**

After a successful test run, you'll get:

```
memory_test_results/
├── device_memory_test_1672876543_valgrind.xml    # Raw profiling log
├── device_memory_test_1672876543_report.html     # Interactive HTML report
├── device_memory_test_1672876543_data.csv        # Detailed leak data
└── device_memory_test_1672876543_summary.json    # Complete session summary
```

### Session Summary Example
```json
{
  "session_id": "device_memory_test_1672876543",
  "start_time": "2025-07-20T21:09:03.123456",
  "end_time": "2025-07-20T21:15:47.654321",
  "status": "completed",
  "device": {
    "hostname": "192.168.1.100",
    "port": 22
  },
  "target_process": {
    "pid": 1234,
    "name": "netconfd",
    "command": "/usr/bin/netconfd --foreground"
  },
  "profiling": {
    "type": "valgrind",
    "output_file": "/tmp/memory_analysis/device_memory_test_1672876543_profiling_valgrind.xml"
  },
  "rpc_results": {
    "get_config_startup": [
      {
        "operation": "get_config_startup",
        "iteration": 1,
        "duration": 0.234,
        "status": "success"
      }
    ]
  },
  "analysis_results": {
    "total_leaks": 15,
    "total_bytes": 8192,
    "by_severity": {"HIGH": 3, "MEDIUM": 7, "LOW": 5}
  }
}
```

## 🎯 **Usage Scenarios**

### Development Testing
Quick memory check during development:
```bash
python device_memory_tester.py \
    --device-host dev-device \
    --device-user developer \
    --device-password dev123 \
    --profiler asan \
    --rpc-dir ./quick_tests \
    --session-name dev_check
```

### Nightly Regression Testing
Comprehensive automated testing:
```bash
python device_memory_tester.py \
    --device-host test-lab-01 \
    --device-user testuser \
    --device-key ~/.ssh/test_key \
    --profiler valgrind \
    --profiler-timeout 7200 \
    --rpc-dir ./comprehensive_tests \
    --session-name nightly_$(date +%Y%m%d) \
    --output-dir ./nightly_results
```

### CI/CD Integration
```bash
# In Jenkins/GitLab CI
python device_memory_tester.py \
    --device-host $DEVICE_IP \
    --device-user $DEVICE_USER \
    --device-password $DEVICE_PASSWORD \
    --profiler valgrind \
    --rpc-dir ./ci_tests \
    --session-name build_$BUILD_NUMBER \
    --output-dir ./artifacts/memory_tests
```

### Performance Testing
Memory behavior under load:
```bash
python device_memory_tester.py \
    --device-host perf-device \
    --device-user perftest \
    --device-password perf123 \
    --profiler asan \
    --rpc-dir ./load_tests \
    --session-name perf_test \
    --no-cleanup  # Keep files for analysis
```

## ⚡ **Advanced Features**

### Custom RPC Operations
Create programmatic RPC operations:
```python
from src.device.netconf_client import RpcOperation

# Stress test with many operations
stress_test = RpcOperation(
    name="stress_test_config",
    xml_content="<get-config><source><running/></source></get-config>",
    description="Stress test configuration retrieval",
    repeat_count=100,
    delay_between_repeats=0.1
)
```

### Custom Profiling Configuration
```python
from src.device.memory_profiler import ProfilingConfig

# Extended Valgrind options
config = ProfilingConfig(
    profiler_type="valgrind",
    valgrind_options=[
        "--tool=memcheck",
        "--leak-check=full",
        "--show-leak-kinds=all",
        "--track-origins=yes",
        "--xml=yes",
        "--num-callers=50",      # More stack frames
        "--freelist-vol=20000000" # Longer free lists
    ],
    session_timeout=7200  # 2 hours
)
```

### Automated Integration
```python
from src.device.integration_manager import IntegrationManager, TestConfig

# Complete programmatic test
manager = IntegrationManager()
test_config = TestConfig(
    session_name="automated_regression",
    device_config=device_config,
    netconf_config=netconf_config,
    profiling_config=profiling_config,
    rpc_operations=rpc_operations,
    output_directory=Path("./results"),
    auto_analyze=True,
    generate_reports=True
)

session_id = manager.start_test_session(test_config)
```

## 🔍 **Troubleshooting**

### Connection Issues
```bash
# Test SSH connectivity
ssh admin@192.168.1.100

# Test NETCONF connectivity
ssh -p 830 admin@192.168.1.100 -s netconf
```

### Permission Issues
```bash
# Ensure user can run profiling tools
sudo setcap cap_sys_ptrace=eip /usr/bin/valgrind

# Check process permissions
ps aux | grep netconf
```

### Profiling Issues
```bash
# Check if Valgrind is installed
which valgrind
valgrind --version

# Check if ASan is available
ldd /path/to/netconf_app | grep asan
```

### Memory Issues
```bash
# Monitor device resources
df -h  # Disk space
free -h  # Memory usage
```

## 🔒 **Security Considerations**

- **Use SSH keys** instead of passwords when possible
- **Limit SSH user permissions** to minimum required
- **Monitor device resources** during profiling
- **Clean up remote files** after testing
- **Secure storage** of profiling logs (may contain sensitive data)

## 📈 **Integration with CI/CD**

### Jenkins Pipeline Example
```groovy
pipeline {
    agent any
    
    environment {
        DEVICE_IP = credentials('device-ip')
        DEVICE_USER = credentials('device-user')
        DEVICE_PASSWORD = credentials('device-password')
    }
    
    stages {
        stage('Memory Leak Testing') {
            steps {
                sh '''
                    python device_memory_tester.py \
                        --device-host $DEVICE_IP \
                        --device-user $DEVICE_USER \
                        --device-password $DEVICE_PASSWORD \
                        --profiler valgrind \
                        --rpc-dir ./test_rpcs \
                        --session-name build_${BUILD_NUMBER} \
                        --output-dir ./memory_results
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'memory_results/**/*'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'memory_results',
                        reportFiles: '*_report.html',
                        reportName: 'Memory Leak Report'
                    ])
                }
            }
        }
    }
}
```

### GitLab CI Example
```yaml
memory_leak_test:
  stage: test
  script:
    - python device_memory_tester.py
        --device-host $DEVICE_IP
        --device-user $DEVICE_USER
        --device-password $DEVICE_PASSWORD
        --profiler valgrind
        --rpc-dir ./test_rpcs
        --session-name $CI_PIPELINE_ID
        --output-dir ./memory_results
  artifacts:
    reports:
      junit: memory_results/*_report.xml
    paths:
      - memory_results/
    expire_in: 1 week
```

## 🎉 **Complete Example**

Here's a complete end-to-end example:

```bash
# 1. Create test RPC files
python device_memory_tester.py --create-sample-rpcs ./netconf_tests

# 2. Verify device connectivity
python device_memory_tester.py \
    --device-host 192.168.1.100 \
    --device-user admin \
    --device-password admin123 \
    --test-connection

# 3. Check for NETCONF processes
python device_memory_tester.py \
    --device-host 192.168.1.100 \
    --device-user admin \
    --device-password admin123 \
    --list-processes

# 4. Run comprehensive memory test
python device_memory_tester.py \
    --device-host 192.168.1.100 \
    --device-user admin \
    --device-password admin123 \
    --profiler valgrind \
    --rpc-dir ./netconf_tests \
    --session-name comprehensive_test \
    --output-dir ./results \
    --log-level INFO

# 5. View results
open results/comprehensive_test_*_report.html
```

This will:
1. ✅ Connect to your device via SSH
2. 🔍 Find running NETCONF processes
3. 📊 Attach Valgrind to monitor memory
4. 🔄 Execute your RPC operations
5. 📁 Download and analyze profiling logs  
6. 📈 Generate interactive HTML reports
7. 💾 Export detailed CSV data

**You now have a complete enterprise-grade solution for device-based NETCONF memory leak testing!** 🚀 