---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: 'bug'
assignees: ''

---

## 🐛 Bug Description

A clear and concise description of what the bug is.

## 🔍 Steps to Reproduce

Steps to reproduce the behavior:

1. Configure device with '...'
2. Run command '....'
3. Check output '....'
4. See error

## ✅ Expected Behavior

A clear and concise description of what you expected to happen.

## ❌ Actual Behavior

A clear and concise description of what actually happened.

## 📊 Environment

**System Information:**
- OS: [e.g. Ubuntu 20.04, macOS 12.1, Windows 11]
- Python Version: [e.g. 3.9.2]
- Tool Version: [e.g. 1.0.0]

**Device Information:**
- Device Type: [e.g. Router, Switch, Server]
- OS/Platform: [e.g. Linux, IOS-XR, Junos]
- Container Runtime: [e.g. Docker 20.10.8, Podman 3.4.2]

**Configuration:**
```yaml
# Paste your configuration file (remove sensitive information)
devices:
  test_device:
    connection:
      hostname: "REDACTED"
      # ... rest of config
```

## 📝 Command and Output

**Command Used:**
```bash
python parallel_device_tester.py --config config/my_device.yaml
```

**Error Output:**
```
# Paste the error output here
```

**Log Files:**
```
# Paste relevant log entries (remove sensitive information)
```

## 📁 Additional Files

If applicable, attach:
- [ ] Configuration files (with credentials removed)
- [ ] Log files (with sensitive data removed)
- [ ] Valgrind XML files (sample)
- [ ] Screenshots of GUI issues

## 🔧 Possible Solution

If you have ideas on how to fix the issue, please describe them here.

## 📋 Additional Context

Add any other context about the problem here:

- Does this happen consistently or intermittently?
- Did this work in a previous version?
- Are you using any custom modifications?
- Any workarounds you've found?

## ✅ Checklist

- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have removed all sensitive information (passwords, IPs, keys)
- [ ] I have provided enough information to reproduce the issue
- [ ] I have tested with the latest version
- [ ] I have checked the documentation and README 