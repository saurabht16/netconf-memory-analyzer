# 🌐 Network Device Setup Guide

This guide explains how to configure the NETCONF Memory Analyzer for network devices that require diagnostic shell access and sudo privileges for Docker operations.

## 🎯 Common Network Device Patterns

Many network devices have this access pattern:
```bash
# 1. SSH to device (management shell)
ssh admin@192.168.1.100

# 2. Enter diagnostic shell to access Docker
admin@device$ diag shell host

# 3. Use sudo for Docker commands
root@device# sudo docker ps
```

## ✅ Automatic Configuration

The analyzer handles this **automatically** with these settings:

### Configuration Example:
```yaml
devices:
  network_device:
    connection:
      hostname: "192.168.1.100"
      username: "admin"
      password: "your_password"
      
      # Network device specific settings
      use_diag_shell: true              # Auto-enter diagnostic shell
      use_sudo_docker: true             # Use sudo for Docker commands
      diag_command: "diag shell host"   # Diagnostic shell command
```

## 🔄 How It Works

### 1. **Connection Sequence**
```bash
[INFO] Connecting to device 192.168.1.100:22
[INFO] SSH connection established
[INFO] Testing Docker access in management shell...
[DEBUG] Command: docker --version (failed)
[INFO] Entering diagnostic shell: diag shell host
[INFO] Testing Docker access with sudo...
[DEBUG] Command: sudo docker --version (success)
[INFO] Configuration complete: diag shell + sudo Docker
```

### 2. **Automatic Command Transformation**
```python
# User command:
"docker ps"

# Automatically becomes:
"diag shell host -c 'sudo docker ps'"
```

### 3. **Smart Detection**
- Tests Docker access without modifications first
- Only uses diag shell if needed
- Only adds sudo if required
- Logs all transformations for debugging

## ⚙️ Configuration Options

### Basic Network Device:
```yaml
devices:
  cisco_device:
    connection:
      hostname: "192.168.1.100"
      username: "admin"
      password: "password"
      use_diag_shell: true     # Default: true
      use_sudo_docker: true    # Default: true
```

### Custom Diagnostic Commands:
```yaml
devices:
  custom_device:
    connection:
      hostname: "192.168.1.101"
      username: "admin"
      password: "password"
      diag_command: "bash"     # Some devices use different commands
      # or "run shell" or "enable shell"
```

### Linux Server (No Special Handling):
```yaml
devices:
  linux_server:
    connection:
      hostname: "192.168.1.200"
      username: "admin"
      password: "password"
      use_diag_shell: false    # Skip diagnostic shell
      use_sudo_docker: true    # May still need sudo
```

### Docker Without Sudo:
```yaml
devices:
  docker_host:
    connection:
      hostname: "192.168.1.300"
      username: "dockeruser"
      password: "password"
      use_diag_shell: false    # Direct Docker access
      use_sudo_docker: false   # User in docker group
```

## 🧪 Testing Your Configuration

### Step 1: Create Configuration
```bash
python create_production_config.py simple \
    --device-ip 192.168.1.100 \
    --username admin \
    --password your_password \
    --container-id netconf-ui \
    --output config/my_device.yaml
```

### Step 2: Test Connectivity
```bash
# This will test the diagnostic shell and sudo setup
python parallel_device_tester.py --config config/my_device.yaml --discover
```

Expected output:
```
[INFO] Connecting to device 192.168.1.100:22
[INFO] SSH connection established
[INFO] Entering diagnostic shell: diag shell host
[INFO] Docker accessible with sudo
[INFO] 📦 Found containers:
  - netconf-ui (running)
  - netconf-backend (running)
```

### Step 3: Dry Run
```bash
# Safe test without actual profiling
python parallel_device_tester.py --config config/my_device.yaml --dry-run
```

## 🔧 Troubleshooting

### Issue: "Failed to enter diagnostic shell"
```
[ERROR] Failed to enter diagnostic shell: diag shell host
```

**Solutions:**
1. **Check command**: Try different diagnostic commands:
   ```yaml
   diag_command: "bash"           # Some devices
   diag_command: "run shell"      # Juniper devices  
   diag_command: "enable shell"   # Some Cisco
   ```

2. **Check permissions**: User may not have diagnostic access
3. **Manual test**: SSH manually and try the command

### Issue: "Docker command failed with sudo"
```
[ERROR] sudo docker ps failed with exit code 1
```

**Solutions:**
1. **Check sudo setup**: User may not have sudo privileges
2. **Try without sudo**: Set `use_sudo_docker: false`
3. **Manual test**: SSH and run `sudo docker ps` manually

### Issue: "Command timeout in diagnostic shell"
```
[ERROR] Command execution timeout after 30 seconds
```

**Solutions:**
1. **Increase timeout**: Diagnostic shells can be slow
   ```yaml
   connection:
     timeout: 60  # Increase from default 30
   ```

2. **Check shell responsiveness**: May be overloaded

### Issue: "Docker not found even with diagnostic shell"
```
[WARNING] Docker still not accessible after entering diagnostic shell
```

**Solutions:**
1. **Check Docker installation**: May not be installed
2. **Check PATH**: Docker may be in different location
3. **Try full path**: `sudo /usr/bin/docker ps`

## 📊 Command Transformation Examples

### Example 1: Simple Docker Command
```yaml
# Configuration:
use_diag_shell: true
use_sudo_docker: true

# Input: "docker ps"
# Output: "diag shell host -c 'sudo docker ps'"
```

### Example 2: Docker Exec
```yaml
# Input: "docker exec -it container_id bash"  
# Output: "diag shell host -c 'sudo docker exec -it container_id bash'"
```

### Example 3: Non-Docker Command
```yaml
# Input: "show version"
# Output: "show version"  (no transformation)
```

## 🎛️ Advanced Configuration

### Multiple Device Types:
```yaml
devices:
  # Cisco network device
  cisco_router:
    connection:
      hostname: "192.168.1.100"
      use_diag_shell: true
      use_sudo_docker: true
      diag_command: "diag shell host"
  
  # Juniper device  
  juniper_switch:
    connection:
      hostname: "192.168.1.101"
      use_diag_shell: true
      use_sudo_docker: true
      diag_command: "run shell"
  
  # Regular Linux server
  linux_host:
    connection:
      hostname: "192.168.1.102"
      use_diag_shell: false
      use_sudo_docker: true
```

### Environment-Specific Settings:
```yaml
# Production devices (secure)
production_device:
  connection:
    use_diag_shell: true
    use_sudo_docker: true
    timeout: 60           # Longer timeout for production

# Development devices (direct access)
dev_device:
  connection:
    use_diag_shell: false
    use_sudo_docker: false
    timeout: 30
```

## ✅ Best Practices

1. **🧪 Test First**: Always use `--discover` to verify setup
2. **📝 Log Review**: Check logs for transformation details
3. **⏱️ Timeout Tuning**: Increase timeout for slow devices
4. **🔐 Security**: Use SSH keys instead of passwords when possible
5. **📋 Documentation**: Document device-specific commands

## 🚀 Quick Start Commands

```bash
# 1. Create config with network device defaults
python create_production_config.py simple \
    --device-ip YOUR_DEVICE_IP \
    --username admin \
    --password PASSWORD \
    --container-id CONTAINER_NAME

# 2. Test the setup
python parallel_device_tester.py --config config/my_device.yaml --discover

# 3. Run safe test
python parallel_device_tester.py --config config/my_device.yaml --dry-run

# 4. Run full analysis
python complete_device_analysis.py --config config/my_device.yaml
```

---

**🎯 The configuration automatically handles the complexity of network device access patterns, so you can focus on memory analysis rather than device connectivity details.** 