# Contributing to NETCONF Memory Leak Analyzer

Thank you for your interest in contributing to the NETCONF Memory Leak Analyzer! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues
- **Bug Reports**: Use the bug report template to describe the issue
- **Feature Requests**: Use the feature request template for new functionality
- **Documentation**: Help improve documentation and examples
- **Testing**: Add test cases and improve test coverage

### Development Process

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/netconf-memory-analyzer.git
   cd netconf-memory-analyzer
   ```

2. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Your Changes**
   - Follow the coding standards below
   - Add tests for new functionality
   - Update documentation as needed

5. **Test Your Changes**
   ```bash
   # Run tests
   pytest

   # Run linting
   flake8 .
   black --check .

   # Test with real devices (optional)
   python parallel_device_tester.py --config config/test_device.yaml --dry-run
   ```

6. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**
   - Use the pull request template
   - Link to related issues
   - Describe changes and testing performed

## 📝 Coding Standards

### Python Style
- **PEP 8 compliance**: Use `black` for formatting
- **Type hints**: Add type annotations where appropriate
- **Docstrings**: Use Google-style docstrings
- **Line length**: Maximum 120 characters

### Code Quality
- **Functions**: Keep functions focused and under 50 lines
- **Classes**: Follow single responsibility principle
- **Error handling**: Use appropriate exception handling
- **Logging**: Use the logging module instead of print statements

### Example Code Style
```python
def analyze_memory_leaks(log_file: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Analyze memory leaks from log file and generate reports.
    
    Args:
        log_file: Path to Valgrind XML or ASan log file
        output_dir: Directory for output reports
        
    Returns:
        Dictionary containing analysis results
        
    Raises:
        FileNotFoundError: If log file doesn't exist
        ValueError: If log file format is invalid
    """
    logger.info(f"Analyzing log file: {log_file}")
    
    if not log_file.exists():
        raise FileNotFoundError(f"Log file not found: {log_file}")
    
    # Implementation here
    return analysis_results
```

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── unit/                   # Unit tests
│   ├── test_analyzer.py
│   ├── test_device_connector.py
│   └── test_docker_manager.py
├── integration/            # Integration tests
│   ├── test_device_workflow.py
│   └── test_report_generation.py
├── fixtures/               # Test data
│   ├── sample_valgrind.xml
│   └── sample_asan.log
└── conftest.py            # Pytest configuration
```

### Writing Tests
- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test workflows and component interactions
- **Mocking**: Use `unittest.mock` for external dependencies
- **Fixtures**: Create reusable test data
- **Coverage**: Aim for >80% code coverage

### Test Example
```python
import pytest
from unittest.mock import Mock, patch
from src.device.docker_manager import DockerManager

def test_container_discovery():
    """Test container discovery functionality."""
    mock_device = Mock()
    mock_device.execute_command.return_value = (0, "container_output", "")
    
    manager = DockerManager(mock_device)
    containers = manager.find_netconf_containers()
    
    assert len(containers) > 0
    assert containers[0].name == "expected_name"
```

## 📚 Documentation

### Code Documentation
- **Docstrings**: All public functions and classes must have docstrings
- **Type hints**: Use type annotations for function parameters and returns
- **Comments**: Explain complex logic and business rules
- **Examples**: Include usage examples in docstrings

### User Documentation
- **README updates**: Update README.md for new features
- **Configuration**: Document new configuration options
- **Examples**: Add practical usage examples
- **Troubleshooting**: Add common issues and solutions

## 🚀 Feature Development

### New Features
1. **Discuss first**: Open an issue to discuss the feature
2. **Design document**: For major features, create a design document
3. **Backward compatibility**: Maintain compatibility when possible
4. **Configuration**: Add configuration options for new features
5. **Documentation**: Update all relevant documentation

### Device Integration
- **SSH compatibility**: Ensure compatibility with various SSH implementations
- **Container support**: Support multiple container runtimes
- **Error handling**: Robust error handling for network and device issues
- **Security**: Follow security best practices for device access

### Analysis Features
- **Parser extensibility**: Design parsers to be easily extensible
- **Performance**: Consider performance impact on large log files
- **Memory usage**: Efficient memory usage for large datasets
- **Output formats**: Support multiple output formats

## 🔒 Security Guidelines

### Credential Handling
- **No hardcoded credentials**: Never commit credentials to the repository
- **Environment variables**: Use environment variables for sensitive data
- **SSH keys**: Support SSH key-based authentication
- **Logging**: Never log sensitive information

### Device Access
- **Minimal permissions**: Use minimal required permissions
- **Connection security**: Use secure connection methods
- **Cleanup**: Always clean up resources and restore original state
- **Audit trail**: Maintain audit logs for device operations

## 📋 Pull Request Checklist

Before submitting a pull request, ensure:

- [ ] Code follows the style guidelines
- [ ] Tests are added for new functionality
- [ ] All tests pass locally
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] No sensitive information is committed
- [ ] Code is properly commented
- [ ] Type hints are added where appropriate

## 🏷️ Issue Labels

We use the following labels for issues:

- **bug**: Something isn't working
- **enhancement**: New feature or request
- **documentation**: Improvements or additions to documentation
- **good first issue**: Good for newcomers
- **help wanted**: Extra attention is needed
- **priority:high**: High priority issue
- **priority:medium**: Medium priority issue
- **priority:low**: Low priority issue

## 📞 Getting Help

- **Issues**: Open a GitHub issue for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Security**: Email security@example.com for security issues
- **Documentation**: Check the README and documentation first

## 📜 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 🎉 Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md**: List of all contributors
- **Release notes**: Major contributions mentioned in releases
- **GitHub**: Automatic contributor recognition

Thank you for contributing to the NETCONF Memory Leak Analyzer! 