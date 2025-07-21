"""
Pytest configuration and shared fixtures for NETCONF Memory Leak Analyzer tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
import yaml

from src.device.device_connector import DeviceConnector, DeviceConfig, ProcessInfo
from src.device.docker_manager import DockerManager, ContainerInfo


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config_file(temp_dir):
    """Create a sample configuration file for testing."""
    config = {
        'devices': {
            'test_device': {
                'connection': {
                    'hostname': '192.168.1.100',
                    'username': 'admin',
                    'password': 'test123'
                },
                'test_scenarios': [
                    {
                        'name': 'test_scenario',
                        'container_id': 'test-container',
                        'memory_limit': '2g',
                        'profiler': 'valgrind',
                        'profiling_duration': 60
                    }
                ]
            }
        },
        'global_config': {
            'max_parallel_devices': 1,
            'log_level': 'INFO'
        }
    }
    
    config_file = temp_dir / 'test_config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    return config_file


@pytest.fixture
def mock_device_connector():
    """Create a mock DeviceConnector for testing."""
    mock_connector = Mock(spec=DeviceConnector)
    
    # Mock successful command execution
    mock_connector.execute_command.return_value = (0, "success output", "")
    
    # Mock file operations
    mock_connector.upload_file.return_value = True
    mock_connector.download_file.return_value = True
    
    return mock_connector


@pytest.fixture
def mock_docker_manager(mock_device_connector):
    """Create a mock DockerManager for testing."""
    mock_manager = Mock(spec=DockerManager)
    
    # Mock container discovery
    mock_containers = [
        ContainerInfo(
            container_id='test123',
            name='test-container',
            image='test/image:latest',
            status='running',
            memory_limit='2GB',
            memory_usage='1GB',
            cpu_usage='10%',
            ports=['8080:8080'],
            created='2025-01-01'
        )
    ]
    mock_manager.find_netconf_containers.return_value = mock_containers
    
    # Mock process discovery
    mock_processes = [
        ProcessInfo(
            pid=1,
            name='netconfd',
            command='/usr/bin/netconfd --foreground',
            memory_usage=1024,
            cpu_usage=5.0
        )
    ]
    mock_manager.get_container_processes.return_value = mock_processes
    
    # Mock memory operations
    mock_manager.increase_container_memory.return_value = True
    mock_manager.verify_valgrind_in_container.return_value = True
    mock_manager.start_valgrind_in_container.return_value = True
    
    return mock_manager


@pytest.fixture
def device_config():
    """Create a test device configuration."""
    return DeviceConfig(
        hostname='192.168.1.100',
        port=22,
        username='admin',
        password='test123'
    )


@pytest.fixture
def sample_valgrind_xml():
    """Sample Valgrind XML output for testing."""
    return """<?xml version="1.0"?>
<valgrindoutput>
  <protocolversion>4</protocolversion>
  <protocoltool>memcheck</protocoltool>
  <preamble>
    <line>Memcheck, a memory error detector</line>
    <line>Copyright (C) 2002-2017, and GNU GPL'd, by Julian Seward et al.</line>
  </preamble>
  
  <pid>12345</pid>
  <ppid>54321</ppid>
  <tool>memcheck</tool>
  
  <error>
    <unique>0x1</unique>
    <tid>1</tid>
    <kind>Leak_DefinitelyLost</kind>
    <xwhat>
      <text>8 bytes in 1 blocks are definitely lost in loss record 1 of 1</text>
      <leakedbytes>8</leakedbytes>
      <leakedblocks>1</leakedblocks>
    </xwhat>
    <stack>
      <frame>
        <ip>0x4C2C04B</ip>
        <fn>malloc</fn>
        <dir>/usr/include</dir>
        <file>stdlib.h</file>
        <line>42</line>
      </frame>
      <frame>
        <ip>0x400567</ip>
        <fn>main</fn>
        <dir>/app/src</dir>
        <file>main.c</file>
        <line>15</line>
      </frame>
    </stack>
  </error>
  
  <errorcounts>
    <pair>
      <count>1</count>
      <unique>0x1</unique>
    </pair>
  </errorcounts>
</valgrindoutput>"""


@pytest.fixture
def sample_asan_log():
    """Sample AddressSanitizer log output for testing."""
    return """
=================================================================
==12345==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 8 byte(s) in 1 object(s) allocated from:
    #0 0x7f8a8c2c8b10 in malloc (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xdeb10)
    #1 0x556f8b2a1567 in main /app/src/main.c:15:5
    #2 0x7f8a8bf3a82f in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x2082f)

SUMMARY: AddressSanitizer: 8 byte(s) leaked in 1 allocation(s).
"""


@pytest.fixture
def sample_valgrind_file(temp_dir, sample_valgrind_xml):
    """Create a sample Valgrind XML file for testing."""
    valgrind_file = temp_dir / 'test_valgrind.xml'
    with open(valgrind_file, 'w') as f:
        f.write(sample_valgrind_xml)
    return valgrind_file


@pytest.fixture
def sample_asan_file(temp_dir, sample_asan_log):
    """Create a sample ASan log file for testing."""
    asan_file = temp_dir / 'test_asan.log'
    with open(asan_file, 'w') as f:
        f.write(sample_asan_log)
    return asan_file


@pytest.fixture
def mock_ssh_client():
    """Create a mock SSH client for testing."""
    mock_client = Mock()
    mock_client.connect.return_value = None
    mock_client.exec_command.return_value = (Mock(), Mock(), Mock())
    
    # Mock stdout/stderr
    mock_stdout = Mock()
    mock_stdout.read.return_value = b"command output"
    mock_stdout.channel.recv_exit_status.return_value = 0
    
    mock_stderr = Mock()
    mock_stderr.read.return_value = b""
    
    mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
    
    return mock_client


@pytest.fixture(autouse=True)
def clean_test_outputs(temp_dir):
    """Automatically clean up test outputs after each test."""
    yield
    # Cleanup any test outputs
    for pattern in ['*.xml', '*.log', '*.html', '*.csv']:
        for file in temp_dir.glob(pattern):
            file.unlink(missing_ok=True)


@pytest.fixture
def sample_rpc_directory(temp_dir):
    """Create a directory with sample RPC files."""
    rpc_dir = temp_dir / 'sample_rpcs'
    rpc_dir.mkdir()
    
    # Create sample RPC files
    rpc_files = {
        'get_config.xml': '''<?xml version="1.0"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <get-config>
    <source><running/></source>
  </get-config>
</rpc>''',
        'get_interfaces.xml': '''<?xml version="1.0"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <get>
    <filter type="subtree">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
    </filter>
  </get>
</rpc>'''
    }
    
    for filename, content in rpc_files.items():
        with open(rpc_dir / filename, 'w') as f:
            f.write(content)
    
    return rpc_dir


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires real devices)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "device: mark test as requiring device connectivity"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    # Skip integration tests unless specifically requested
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests (requires device configuration)"
    )
    parser.addoption(
        "--device-config",
        action="store",
        default="tests/test_device_config.yaml",
        help="device configuration file for integration tests"
    ) 