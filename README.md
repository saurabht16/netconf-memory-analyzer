# 🔬 NETCONF Device Memory Leak Analyzer

A comprehensive tool for testing, analyzing, and reporting memory leaks in containerized NETCONF applications on remote devices.

## ✨ Features

### 🐳 **Containerized Device Testing**
- **SSH-based device connectivity** with secure authentication
- **Docker container discovery** and process identification
- **Hot memory allocation** (no container restarts required)
- **Pre-built Valgrind/ASan support** (no installation needed)
- **Parallel device testing** with configuration-driven setup

### 📊 **Advanced Memory Analysis**
- **Valgrind XML parsing** with leak classification
- **AddressSanitizer log analysis** with error categorization
- **Impact scoring** based on severity, size, frequency, and location
- **Intelligent filtering** to remove noise and system libraries
- **Historical trend tracking** with SQLite persistence

### 📄 **Professional Reporting**
- **Interactive HTML reports** with filtering and search
- **CSV exports** for spreadsheet analysis and automation
- **Consolidated dashboards** for multiple devices/containers
- **Real-time GUI** for interactive analysis
- **Container-specific recommendations**

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/yourusername/netconf-memory-analyzer
cd netconf-memory-analyzer
pip install -r requirements.txt
```

### Device Configuration

```bash
# Create device configuration
python create_production_config.py simple \
    --device-ip 192.168.1.100 \
    --username admin \
    --password your_password \
    --container-id netconf-ui \
    --output config/my_device.yaml
```

### Discovery and Testing

```bash
# Discover containers and processes
python parallel_device_tester.py --config config/my_device.yaml --discover

# Run complete analysis workflow
python complete_device_analysis.py --config config/my_device.yaml
```

## 📋 Usage Examples

### Single Device Testing
```bash
python parallel_device_tester.py --config config/device.yaml --device my_device
```

### Multiple Device Testing
```bash
python parallel_device_tester.py --config config/devices.yaml
```

### Manual Log Analysis
```bash
python memory_leak_analyzer_enhanced.py \
    --input valgrind_output.xml \
    --output report.html \
    --cleanup --impact-analysis \
    --export-csv data.csv
```

### Interactive GUI
```bash
python memory_leak_analyzer.py --gui
```

## 📁 Project Structure

```
netconf-memory-analyzer/
├── src/device/                     # Device connectivity and profiling
│   ├── device_connector.py         # SSH connection management
│   ├── docker_manager.py           # Container operations
│   ├── containerized_profiler.py   # Memory profiling in containers
│   ├── netconf_client.py           # NETCONF RPC operations
│   └── memory_profiler.py          # Base profiling functionality
├── config/                         # Configuration templates
│   ├── simple_device_config.yaml   # Single device template
│   └── device_configs.yaml         # Multi-device template
├── parallel_device_tester.py       # Main parallel testing tool
├── complete_device_analysis.py     # End-to-end analysis workflow
├── memory_leak_analyzer_enhanced.py # Advanced analysis engine
├── memory_leak_analyzer.py         # GUI analysis tool
└── create_production_config.py     # Configuration generator
```

## 🛠️ Configuration

### Device Configuration Example

```yaml
devices:
  production_device:
    connection:
      hostname: "192.168.1.100"
      username: "admin"
      password: "your_password"
    
    test_scenarios:
      - name: "ui_container_test"
        container_id: "netconf-ui"
        memory_limit: "5g"
        profiler: "valgrind"
        profiling_duration: 120
        restore_memory: true

global_config:
  max_parallel_devices: 3
  log_level: "INFO"
  consolidated_report: true
```

### Profiling Options

- **Valgrind**: Comprehensive memory error detection
- **AddressSanitizer**: Fast runtime memory error detection
- **Hot Memory Updates**: Increase container memory without restarts
- **Process Auto-Discovery**: Automatic NETCONF process identification

## 📊 Report Features

### HTML Reports
- 🎯 **Impact scoring** with HIGH/MEDIUM/LOW prioritization
- 🔍 **Interactive filtering** by file, function, size, type
- 📈 **Memory trend charts** with historical tracking
- 🐳 **Container-specific analysis** and recommendations
- 📱 **Responsive design** for mobile and desktop

### CSV Exports
- 📊 **Spreadsheet-compatible** leak data
- 🤖 **Automation-friendly** format for CI/CD
- 📈 **Historical tracking** for trend analysis
- 🔧 **Custom filtering** capabilities

## 🔧 Advanced Features

### Parallel Testing
- Test multiple devices simultaneously
- Configure parallel limits per device
- Consolidated reporting across all devices

### Container Integration
- Docker container discovery
- Hot memory allocation (no restarts)
- Pre-built profiling tool support
- Container-aware analysis

### Production Safety
- Automatic memory restoration
- Error handling and cleanup
- SSH key authentication support
- Comprehensive logging

## 📖 Documentation

- [Configuration Guide](config/README_CONFIG.md)
- [Device Testing Guide](README_DEVICE_TESTING.md)
- [Project Summary](SUMMARY.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues, questions, or contributions:
- 📝 **Issues**: [GitHub Issues](https://github.com/yourusername/netconf-memory-analyzer/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/netconf-memory-analyzer/discussions)
- 📧 **Email**: your.email@example.com

## 🎯 Key Benefits

- ✅ **Zero-downtime testing** with hot memory updates
- ✅ **Production-ready** with automatic cleanup and restoration
- ✅ **Scalable** parallel testing across multiple devices
- ✅ **Professional reporting** with interactive HTML and CSV exports
- ✅ **Container-optimized** for modern NETCONF deployments
- ✅ **Configuration-driven** for easy automation and CI/CD integration

---

**Made with ❤️ for the NETCONF community** 