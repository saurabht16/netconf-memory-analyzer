# 🛠️ Development Guide

**Technical documentation for NETCONF Memory Leak Analyzer developers**

## 🏗️ Architecture Overview

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  memory_tester  │───▶│  device_manager │───▶│ docker_manager  │
│   (main app)    │    │  (SSH+network)  │    │ (containers)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   analyzers     │    │ netconf_client  │    │   configurable  │
│ (leak analysis) │    │ (RPC testing)   │    │     setup       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Principles

1. **Efficiency First** - Targeted operations, early termination
2. **Safety** - Automatic backups, cleanup, restoration
3. **Flexibility** - Configurable everything via YAML
4. **Reliability** - Comprehensive error handling and recovery

## 🧹 Recent Major Improvements

### Code Cleanup (2024)
- **Removed 8 redundant files** (~2000+ lines eliminated)
- **57% reduction** in total code lines
- **87% reduction** in testing scripts
- **100% elimination** of duplicate functions
- **Clean separation of concerns**

### Efficiency Optimizations (2024)
- **75% faster container discovery** (10-20s → 2-5s)
- **70% reduction in Docker commands** (10+ → 2-4)
- **90% reduction in container processing** (all → target only)
- **Targeted search with early termination**

### Process Management Fixes (2024)
- **Comprehensive NETCONF process killing** (multiple strategies)
- **Proper Valgrind command construction** (options → target)
- **All Docker commands use sudo** (network device compatibility)
- **Diagnostic shell integration** (`diag shell host` support)

### Configurable Container Setup (2024)
- **Custom command sequences** (pre/post commands)
- **Safe file editing** with automatic backups
- **Template variable substitution** ({{container_id}}, etc.)
- **Cleanup and restoration** workflows

## 🔧 Technical Architecture

### Device Management Layer
```python
# src/device/device_connector.py
class DeviceConnector:
    """SSH connectivity with network device support"""
    - SSH connection management
    - Diagnostic shell integration (diag shell host)
    - Sudo command wrapping
    - Network device compatibility

# src/device/docker_manager.py  
class DockerManager:
    """Docker container operations"""
    - Efficient container discovery
    - Process lifecycle management
    - Memory hot updates
    - Valgrind integration

# src/device/configurable_container_setup.py
class ConfigurableContainerSetup:
    """Custom container preparation"""
    - Command sequence execution
    - File editing with backups
    - Template variable substitution
    - Cleanup workflows
```

### Analysis Layer
```python
# parsers/ - Log file parsing
ValgrindParser  # Parse Valgrind XML
AsanParser      # Parse AddressSanitizer logs

# analysis/ - Advanced analysis
ImpactAnalyzer  # Leak impact scoring
TrendAnalyzer   # Historical comparisons

# reports/ - Report generation  
HTMLGenerator   # Interactive HTML reports
CSVExporter     # Data export
```

### Application Layer
```python
# memory_tester.py - Main orchestrator
class MemoryTester:
    """Unified testing interface"""
    - Device discovery and testing
    - Configuration-driven workflows
    - Parallel execution
    - Result analysis integration

# memory_leak_analyzer_enhanced.py - Advanced analysis
# memory_leak_analyzer.py - Basic analysis + GUI
```

## 🔄 Development Workflow

### 1. Setup Development Environment
```bash
# Clone repository
git clone <repository-url>
cd Netconf

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy
```

### 2. Code Standards

**Python Style:**
```bash
# Code formatting
black src/ tests/ *.py

# Linting
flake8 src/ tests/ *.py

# Type checking  
mypy src/
```

**Naming Conventions:**
- Classes: `PascalCase` (e.g., `DockerManager`)
- Functions/methods: `snake_case` (e.g., `find_netconf_processes`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- Files: `snake_case.py` (e.g., `docker_manager.py`)

### 3. Testing Strategy

**Unit Tests:**
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_docker_manager.py

# Coverage report
pytest --cov=src tests/
```

**Integration Tests:**
```bash
# Test with real devices (update config first)
python test_netconf_cleanup.py
python test_efficient_discovery.py  
python test_configurable_setup.py
```

**Validation Tests:**
```bash
# Always test with dry run
python memory_tester.py --config config/test.yaml --test --dry-run
```

### 4. Adding New Features

**Example: Adding New Profiler Support**

1. **Update configuration schema:**
```yaml
# Add to global_config/default_container_setup
profiler_options:
  custom_profiler:
    command: "custom_profiler --option=value {target_command}"
    output_format: "xml"
    file_extension: ".xml"
```

2. **Extend docker_manager.py:**
```python
def start_custom_profiler_in_container(self, container_id, options):
    """Start custom profiler in container"""
    # Implementation here
    pass
```

3. **Update parser layer:**
```python
# src/parsers/custom_profiler_parser.py
class CustomProfilerParser:
    """Parse custom profiler output"""
    def parse_file(self, file_path):
        # Implementation here
        pass
```

4. **Add tests:**
```python
# tests/test_custom_profiler.py
def test_custom_profiler_integration():
    # Test implementation
    pass
```

## 🐛 Debugging Guide

### Common Development Issues

**1. SSH Connection Problems**
```python
# Enable debug logging
logging.getLogger('paramiko').setLevel(logging.DEBUG)

# Test connection manually
with DeviceConnector(config) as device:
    result = device.execute_command("echo test")
    print(result)
```

**2. Docker Command Failures**
```python
# Check Docker access
docker_manager = DockerManager(device)
containers = docker_manager.list_containers()
print(f"Found {len(containers)} containers")

# Test with sudo
exit_code, stdout, stderr = device.execute_command("sudo docker ps")
print(f"Exit code: {exit_code}")
```

**3. Process Management Issues**
```python
# Debug process finding
processes = docker_manager.find_netconf_processes_in_container(container_id)
for proc in processes:
    print(f"PID {proc.pid}: {proc.command}")

# Test process killing
success = docker_manager.kill_netconf_processes_in_container(container_id)
print(f"Kill success: {success}")
```

### Performance Profiling

**Profile Container Discovery:**
```python
import time

start = time.time()
target_container = docker_manager.find_target_netconf_container()
end = time.time()
print(f"Discovery took {end - start:.2f} seconds")
```

**Profile Memory Updates:**
```python
start = time.time()
success = docker_manager.increase_container_memory(container_id, "5g")
end = time.time()
print(f"Memory update took {end - start:.2f} seconds")
```

## 📋 Configuration Management

### Adding New Configuration Options

1. **Update configuration schema:**
```python
# src/device/device_connector.py
@dataclass
class DeviceConfig:
    # Add new field
    new_option: bool = False
    new_setting: str = "default_value"
```

2. **Update YAML templates:**
```yaml
# config/simple_device_config.yaml
connection:
  new_option: true
  new_setting: "custom_value"
```

3. **Handle in implementation:**
```python
def some_method(self):
    if self.config.new_option:
        # Use new behavior
        pass
    else:
        # Use default behavior
        pass
```

### Configuration Validation

```python
def validate_config(config_dict):
    """Validate configuration before use"""
    required_fields = ['hostname', 'username']
    for field in required_fields:
        if field not in config_dict:
            raise ValueError(f"Missing required field: {field}")
    
    # Additional validation logic
    pass
```

## 🔐 Security Considerations

### SSH Key Management
```python
# Prefer SSH keys over passwords
device_config = DeviceConfig(
    hostname="device.example.com",
    username="admin", 
    key_file="/path/to/private/key",  # Preferred
    # password="password"             # Avoid in production
)
```

### Credential Storage
```bash
# Never commit credentials to git
echo "*.yaml" >> .gitignore
echo "config/production_*" >> .gitignore

# Use environment variables
export DEVICE_PASSWORD="secure_password"
```

### Container Security
```python
# Always use sudo for Docker operations on network devices
if self.config.use_sudo_docker:
    docker_cmd = f"sudo {docker_cmd}"

# Validate container IDs to prevent injection
if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', container_id):
    raise ValueError("Invalid container ID")
```

## 📊 Performance Monitoring

### Metrics to Track
- Container discovery time
- Memory update duration  
- Process management success rate
- Valgrind startup time
- Analysis completion time

### Logging Best Practices
```python
# Use structured logging
self.logger.info("Starting operation", extra={
    'operation': 'container_discovery',
    'device': device_name,
    'container_count': len(containers)
})

# Log performance metrics
self.logger.info(f"Container discovery completed in {duration:.2f}s")
```

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Component interaction testing  
3. **End-to-End Tests** - Full workflow testing
4. **Performance Tests** - Speed and efficiency validation
5. **Configuration Tests** - YAML parsing and validation

### Mock Testing
```python
# Mock external dependencies
@patch('src.device.docker_manager.DockerManager')
def test_memory_tester(mock_docker):
    mock_docker.find_target_netconf_container.return_value = mock_container
    # Test implementation
```

### Test Data
```bash
# Create test fixtures
tests/
├── fixtures/
│   ├── sample_valgrind.xml
│   ├── sample_asan.log
│   └── test_configs/
└── conftest.py  # Shared test configuration
```

## 📈 Changelog

### Version 2024.12 (Latest)
**Major Features:**
- ✅ Configurable container setup with custom commands
- ✅ File editing with automatic backups
- ✅ Template variable substitution
- ✅ Enhanced cleanup workflows

**Performance:**
- ✅ 75% faster container discovery
- ✅ 70% reduction in Docker commands
- ✅ Targeted search with early termination

**Bug Fixes:**
- ✅ Comprehensive NETCONF process killing
- ✅ Proper Valgrind command construction
- ✅ All Docker commands use sudo
- ✅ Diagnostic shell integration

**Code Quality:**
- ✅ 57% reduction in total code lines
- ✅ 87% reduction in testing scripts  
- ✅ 100% elimination of duplicate functions
- ✅ Clean architectural separation

### Version 2024.11
**Features:**
- ✅ Efficient container discovery
- ✅ Network device support
- ✅ Hot memory updates
- ✅ Multi-device testing

### Version 2024.10
**Initial Release:**
- ✅ Basic memory leak testing
- ✅ Valgrind integration
- ✅ HTML report generation

## 🤝 Contributing Guidelines

### Pull Request Process

1. **Fork** the repository
2. **Create** feature branch from `main`
3. **Implement** changes with tests
4. **Ensure** all tests pass
5. **Update** documentation
6. **Submit** pull request

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Backward compatibility maintained

### Release Process

1. **Update** version numbers
2. **Update** CHANGELOG.md
3. **Run** full test suite
4. **Create** release tag
5. **Generate** release notes

---

**Happy developing!** 🚀 