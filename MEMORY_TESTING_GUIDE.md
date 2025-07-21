# 🔬 NETCONF Memory Leak Testing & Analysis - Complete Guide

This guide walks you through the entire process of generating memory logs and analyzing them for memory leaks in NETCONF applications.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Device Configuration](#device-configuration)
4. [Running Memory Tests](#running-memory-tests)
5. [Analyzing Generated Logs](#analyzing-generated-logs)
6. [Understanding Results](#understanding-results)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- Python 3.8+
- SSH access to target devices
- Docker/container runtime on target devices
- Valgrind and/or AddressSanitizer pre-installed in containers

### Tool Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/netconf-memory-analyzer.git
cd netconf-memory-analyzer

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## 🛠️ Environment Setup

### Step 1: Install Dependencies
```bash
# Install core dependencies
pip install PyYAML paramiko lxml

# Optional GUI dependencies
pip install tkinter-tooltip matplotlib plotly

# Development tools (optional)
pip install pytest pytest-cov black flake8
```

### Step 2: Verify Installation
```bash
# Test basic functionality
python parallel_device_tester.py --help
python memory_leak_analyzer_enhanced.py --help
```

## ⚙️ Device Configuration

### Step 3: Create Device Configuration

#### Option A: Interactive Configuration
```bash
# Create configuration interactively
python create_production_config.py simple \
    --device-ip 192.168.1.100 \
    --username admin \
    --password your_password \
    --container-id netconf-ui \
    --output config/my_device.yaml
```

#### Option B: Manual Configuration
Create `config/my_device.yaml`:
```yaml
devices:
  production_device:
    connection:
      hostname: "192.168.1.100"
      port: 22
      username: "admin"
      password: "your_password"
      # OR use SSH key:
      # private_key_file: "/path/to/private_key"
    
    test_scenarios:
      - name: "netconf_ui_memory_test"
        container_id: "netconf-ui"
        memory_limit: "5g"
        profiler: "valgrind"  # or "asan"
        profiling_duration: 120
        restore_memory: true
        
        # Optional: Specific process targeting
        target_process: "netconfd"
        
        # Optional: RPC stress testing
        rpc_directory: "test_data/sample_rpcs"
        rpc_count: 50
        rpc_interval: 1.0

global_config:
  max_parallel_devices: 1
  log_level: "INFO"
  consolidated_report: true
  output_directory: "results"
```

### Step 4: Verify Device Connectivity
```bash
# Test connection to your device
python parallel_device_tester.py --config config/my_device.yaml --discover
```

## 🧪 Running Memory Tests

### Step 5: Device Discovery (Optional)
```bash
# Discover containers and processes on device
python parallel_device_tester.py --config config/my_device.yaml --discover

# Sample output:
# 📦 Container: netconf-ui (ID: abc123)
#   📊 Memory: 2GB used / 4GB limit
#   🔄 Processes:
#     - PID 1234: netconfd (/usr/bin/netconfd --foreground)
#     - PID 5678: nginx (nginx: master process)
```

### Step 6: Dry Run (Recommended)
```bash
# Test configuration without actually running profiling
python parallel_device_tester.py --config config/my_device.yaml --dry-run

# This will:
# ✅ Verify SSH connectivity
# ✅ Check container existence
# ✅ Verify Valgrind/ASan availability
# ✅ Test memory increase capability
# ✅ Validate configuration
```

### Step 7: Run Memory Testing

#### Option A: Complete Automated Workflow
```bash
# Run complete testing and analysis workflow
python complete_device_analysis.py --config config/my_device.yaml

# This will:
# 1. Connect to device
# 2. Increase container memory (5GB)
# 3. Start profiling (Valgrind/ASan)
# 4. Execute RPC stress tests
# 5. Stop profiling and collect logs
# 6. Download logs locally
# 7. Analyze logs for memory leaks
# 8. Generate HTML and CSV reports
# 9. Open consolidated report in browser
# 10. Restore original container memory
```

#### Option B: Manual Step-by-Step Testing
```bash
# Run device testing only (generates logs)
python parallel_device_tester.py --config config/my_device.yaml

# Then analyze downloaded logs separately
python memory_leak_analyzer_enhanced.py \
    --input results/production_device/valgrind_output.xml \
    --output analysis_reports/device_analysis.html \
    --cleanup --impact-analysis \
    --export-csv analysis_reports/leaks.csv
```

## 📊 Step-by-Step Testing Process

### What Happens During Testing:

1. **🔗 Device Connection**
   ```
   [INFO] Connecting to device 192.168.1.100:22
   [INFO] SSH connection established
   ```

2. **🐳 Container Management**
   ```
   [INFO] Found container: netconf-ui (ID: abc123)
   [INFO] Current memory limit: 2GB
   [INFO] Increasing memory to 5GB (hot update, no restart)
   [INFO] ✅ Memory updated successfully
   ```

3. **🔍 Process Discovery**
   ```
   [INFO] Scanning container processes...
   [INFO] Found target process: netconfd (PID: 1234)
   [INFO] ✅ Valgrind available in container
   ```

4. **📈 Memory Profiling**
   ```
   [INFO] Starting Valgrind profiling on PID 1234
   [INFO] Profiling command: valgrind --tool=memcheck --leak-check=full --xml=yes --xml-file=/tmp/valgrind_output.xml --track-origins=yes /proc/1234/exe
   [INFO] ✅ Profiling started
   ```

5. **🚀 RPC Stress Testing**
   ```
   [INFO] Executing RPC stress tests...
   [INFO] Sending 50 RPCs with 1.0s intervals
   [INFO] RPC 1/50: get-config.xml [✅ Success - 0.245s]
   [INFO] RPC 2/50: get-interfaces.xml [✅ Success - 0.312s]
   ```

6. **📥 Log Collection**
   ```
   [INFO] Stopping profiling after 120 seconds
   [INFO] Downloading logs: /tmp/valgrind_output.xml
   [INFO] ✅ Downloaded to: results/production_device/valgrind_output.xml
   ```

7. **🔄 Cleanup**
   ```
   [INFO] Restoring original memory limit: 2GB
   [INFO] ✅ Memory restored successfully
   [INFO] 🔌 SSH connection closed
   ```

## 🔬 Analyzing Generated Logs

### Step 8: Log Analysis Options

#### Option A: Enhanced Analyzer (Recommended)
```bash
# Comprehensive analysis with all features
python memory_leak_analyzer_enhanced.py \
    --input results/production_device/valgrind_output.xml \
    --output analysis_reports/comprehensive_report.html \
    --cleanup \
    --impact-analysis \
    --trend-analysis \
    --export-csv analysis_reports/leak_data.csv \
    --filter-system-libs \
    --min-leak-size 64

# Analysis features:
# ✅ Noise reduction (filter system libraries)
# ✅ Impact scoring (HIGH/MEDIUM/LOW priority)
# ✅ Trend analysis with historical data
# ✅ Interactive HTML report with filtering
# ✅ CSV export for spreadsheet analysis
```

#### Option B: GUI Analyzer
```bash
# Interactive GUI for manual analysis
export TK_SILENCE_DEPRECATION=1  # Suppress macOS warnings
python memory_leak_analyzer.py --gui

# GUI Features:
# 🖱️ Drag-and-drop log files
# 🔍 Real-time filtering and search
# 📊 Visual leak statistics
# 💾 Export options
# 🎨 Syntax highlighting
```

#### Option C: Analyze Multiple Files
```bash
# Analyze all logs in results directory
python memory_leak_analyzer_enhanced.py \
    --input results/ \
    --output analysis_reports/consolidated_report.html \
    --cleanup --impact-analysis

# This will analyze:
# - All Valgrind XML files
# - All AddressSanitizer log files
# - Generate consolidated report
```

### Step 9: Understanding Analysis Output

#### Console Output Example:
```
🔬 NETCONF Memory Leak Analyzer v1.0.0

📁 Input: results/production_device/valgrind_output.xml
📊 Processing Valgrind XML file...

🧹 CLEANUP RESULTS:
  • Original leaks: 156
  • After filtering: 23
  • System library leaks removed: 133
  • Duplicate leaks merged: 8

📈 IMPACT ANALYSIS:
  • HIGH priority leaks: 3 (2.1MB total)
  • MEDIUM priority leaks: 12 (856KB total)
  • LOW priority leaks: 8 (124KB total)

💾 EXPORTS:
  ✅ HTML Report: analysis_reports/comprehensive_report.html
  ✅ CSV Data: analysis_reports/leak_data.csv
  ✅ Trends Database: analysis_reports/trends.db

🎯 TOP PRIORITY LEAKS:
  1. 1.2MB in netconf_session_create() [HIGH]
  2. 512KB in xml_parser_init() [HIGH]
  3. 256KB in rpc_handler_allocate() [HIGH]

⏱️ Analysis completed in 3.2 seconds
🌐 Opening report in browser...
```

## 📋 Understanding Results

### Step 10: Reading HTML Reports

The generated HTML report includes:

#### 🎯 **Summary Dashboard**
- Total memory leaked
- Number of unique leak locations  
- Priority distribution (HIGH/MEDIUM/LOW)
- Trend charts (if historical data available)

#### 🔍 **Detailed Leak Table**
- **Location**: File and function where leak occurs
- **Size**: Memory amount leaked
- **Count**: Number of times this leak occurs  
- **Impact**: Priority score (1-100)
- **Category**: Leak type (Definite, Possible, etc.)
- **Stack Trace**: Full call stack

#### 📊 **Interactive Features**
- 🔍 Filter by file, function, size, or impact
- 📈 Sort by any column
- 🎨 Syntax highlighting for code
- 💾 Export filtered results
- 📱 Mobile-responsive design

### Step 11: CSV Analysis

The CSV export contains columns:
```csv
Location,Function,File,Line,Size_Bytes,Count,Impact_Score,Category,Total_Size,Stack_Trace
```

Use for:
- 📊 Spreadsheet analysis (Excel, Google Sheets)
- 🤖 Automated processing and CI/CD
- 📈 Historical trend tracking
- 🔄 Integration with other tools

## 🚀 Advanced Workflows

### Step 12: Multi-Device Testing
```bash
# Create configuration for multiple devices
cat > config/production_devices.yaml << 'EOF'
devices:
  device1:
    connection:
      hostname: "192.168.1.100"
      username: "admin"
      password: "pass1"
    test_scenarios:
      - name: "ui_test"
        container_id: "netconf-ui"
        memory_limit: "5g"
        profiler: "valgrind"
        profiling_duration: 120

  device2:
    connection:
      hostname: "192.168.1.101"
      username: "admin"
      password: "pass2"
    test_scenarios:
      - name: "backend_test"
        container_id: "netconf-backend"
        memory_limit: "8g"
        profiler: "asan"
        profiling_duration: 180

global_config:
  max_parallel_devices: 2
  consolidated_report: true
EOF

# Run parallel testing
python parallel_device_tester.py --config config/production_devices.yaml
```

### Step 13: Continuous Integration
```bash
# Add to CI/CD pipeline
python complete_device_analysis.py \
    --config config/ci_devices.yaml \
    --fail-on-leaks \
    --max-leak-size 1MB \
    --output-format json

# Exit codes:
# 0: No significant leaks found
# 1: High-priority leaks detected
# 2: Analysis failed
```

### Step 14: Historical Tracking
```bash
# Enable trend analysis for continuous monitoring
python memory_leak_analyzer_enhanced.py \
    --input results/daily_logs/ \
    --trend-analysis \
    --trend-database /var/lib/netconf/trends.db \
    --alert-on-increase 10%

# This tracks:
# 📈 Leak size trends over time
# 📊 New vs resolved leaks
# 🚨 Regression detection
# 📧 Automated alerts
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 🔌 Connection Issues
```bash
# SSH connection fails
ERROR: Authentication failed for 192.168.1.100

Solutions:
1. Verify credentials in config file
2. Test manual SSH: ssh admin@192.168.1.100
3. Check firewall settings
4. Use SSH key authentication instead
```

#### 🐳 Container Issues
```bash
# Container not found
ERROR: Container 'netconf-ui' not found

Solutions:
1. Run discovery: --discover
2. Check container name: docker ps
3. Verify container is running
4. Update container_id in config
```

#### 🔧 Profiling Issues
```bash
# Valgrind not available
ERROR: Valgrind not found in container

Solutions:
1. Verify pre-built image has Valgrind
2. Check container PATH
3. Try AddressSanitizer instead
4. Install Valgrind in base image
```

#### 📁 File Analysis Issues
```bash
# Log file format issues
ERROR: Invalid XML format in valgrind_output.xml

Solutions:
1. Check profiling completed successfully
2. Verify file wasn't truncated
3. Check disk space on device
4. Re-run profiling with longer duration
```

### Getting Help

- 📖 **Documentation**: Check README.md and CONTRIBUTING.md
- 🐛 **Issues**: Open GitHub issue with error details
- 💬 **Discussions**: Use GitHub Discussions for questions
- 🔒 **Security**: Email security issues to security@example.com

## 📝 Quick Reference Commands

```bash
# Basic workflow
python create_production_config.py simple --device-ip IP --username USER
python parallel_device_tester.py --config CONFIG --discover
python parallel_device_tester.py --config CONFIG --dry-run
python complete_device_analysis.py --config CONFIG

# Manual analysis
python memory_leak_analyzer_enhanced.py --input FILE --output REPORT.html
python memory_leak_analyzer.py --gui

# Advanced features
python parallel_device_tester.py --config CONFIG --device SPECIFIC_DEVICE
python memory_leak_analyzer_enhanced.py --input DIR/ --trend-analysis
```

---

**🎯 Success Criteria**: After following this guide, you should have:
- ✅ Memory logs generated from your NETCONF devices
- ✅ Interactive HTML reports showing leak details
- ✅ CSV data for further analysis
- ✅ Understanding of leak priorities and impact
- ✅ Automated workflow for continuous monitoring

**Next Steps**: Set up regular testing schedules and integrate with your CI/CD pipeline for continuous memory leak monitoring. 