# Changelog

All notable changes to the NETCONF Memory Leak Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-20

### Added
- **Containerized Device Testing**: Complete Docker container integration with hot memory updates
- **Parallel Device Testing**: Configuration-driven testing across multiple devices simultaneously
- **Advanced Log Analysis**: Enhanced Valgrind XML and AddressSanitizer log parsing with impact scoring
- **Interactive HTML Reports**: Professional reporting with filtering, search, and visualization
- **CSV Export**: Spreadsheet-compatible data export for automation and trend analysis
- **Configuration Management**: YAML-based device and test scenario configuration
- **SSH Device Connectivity**: Secure device access with key-based and password authentication
- **Process Auto-Discovery**: Automatic identification of NETCONF processes in containers
- **Memory Impact Scoring**: Intelligent prioritization based on severity, size, and frequency
- **Historical Trend Tracking**: SQLite-based persistence for leak trend analysis
- **GUI Analysis Tool**: Interactive desktop application for real-time analysis
- **Production Safety Features**: Automatic cleanup, memory restoration, and error handling

### Features
- Zero-downtime container memory allocation (no restarts required)
- Pre-built Valgrind/AddressSanitizer support (no installation needed)
- Container-aware leak analysis with specific recommendations
- Consolidated reporting across multiple devices and containers
- Real-time memory monitoring during profiling sessions
- Comprehensive filtering to remove system library noise
- Cross-platform support (Linux, macOS, Windows)

### Configuration
- Device connection management with SSH key support
- Flexible test scenario definition with multiple containers per device
- Global configuration for parallel execution limits
- NETCONF RPC stress testing integration
- Customizable profiling duration and memory limits

### Documentation
- Complete setup and usage guides
- Configuration file documentation
- API documentation for all modules
- Example configurations for common use cases
- Troubleshooting guide

### Security
- Secure credential handling
- SSH key authentication support
- No credential storage in logs or reports
- Safe container operations with automatic rollback

## [Unreleased]

### Planned
- Kubernetes integration for orchestrated environments
- Prometheus/Grafana integration for monitoring
- Web-based dashboard for enterprise deployments
- Advanced anomaly detection using machine learning
- Integration with popular CI/CD platforms (Jenkins, GitLab CI, GitHub Actions)
- REST API for programmatic access
- Plugin system for custom analysis modules 