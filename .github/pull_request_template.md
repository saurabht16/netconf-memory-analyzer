# Pull Request

## 📋 Description

Brief description of what this PR does and why.

Fixes #(issue_number)

## 🔄 Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🧹 Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test improvements
- [ ] 🔧 Configuration changes

## 🎯 Changes Made

Detailed description of changes:

- **Added**: List new functionality
- **Changed**: List modified functionality  
- **Fixed**: List bug fixes
- **Removed**: List deprecated/removed functionality

## 🧪 Testing

Describe the tests you ran to verify your changes:

### Unit Tests
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Test coverage maintained/improved

### Integration Tests
- [ ] Device connection tests pass
- [ ] Container operation tests pass
- [ ] Report generation tests pass

### Manual Testing
- [ ] Tested with real devices
- [ ] Tested with sample data
- [ ] Tested error scenarios

**Test Configuration:**
```yaml
# Include test configuration used (remove sensitive data)
```

**Test Commands:**
```bash
# List commands used for testing
pytest tests/
python parallel_device_tester.py --config test_config.yaml --dry-run
```

## 📊 Performance Impact

- [ ] No performance impact
- [ ] Performance improved
- [ ] Performance degraded (explain why acceptable)

**Performance Notes:**
<!-- Describe any performance considerations -->

## 💻 Environment Tested

- **OS**: [e.g. Ubuntu 20.04, macOS 12.1]
- **Python**: [e.g. 3.9.2]
- **Dependencies**: [list any new/updated dependencies]

## 📸 Screenshots

If applicable, add screenshots to help explain your changes.

## 📚 Documentation

- [ ] Code comments updated
- [ ] README.md updated
- [ ] CHANGELOG.md updated
- [ ] Configuration documentation updated
- [ ] API documentation updated

## ✅ Checklist

### Code Quality
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation

### Testing
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

### Security
- [ ] I have not introduced any security vulnerabilities
- [ ] No sensitive information (credentials, keys, IPs) is included
- [ ] Error handling doesn't expose sensitive information

### Compatibility
- [ ] My changes are backward compatible
- [ ] I have considered the impact on existing configurations
- [ ] Breaking changes are clearly documented

## 🔗 Related Issues

- Closes #123
- Related to #456
- Depends on #789

## 📋 Additional Notes

Any additional information, concerns, or notes for reviewers:

<!-- 
- Special considerations
- Areas that need extra review
- Known limitations
- Future improvements planned
-->

## 🚀 Deployment Notes

Any special considerations for deployment:

- [ ] No special deployment steps needed
- [ ] Configuration changes required
- [ ] Database migration needed
- [ ] Dependency updates required

---

## For Reviewers

### 🔍 Review Focus Areas

Please pay special attention to:

- [ ] Security implications
- [ ] Performance impact
- [ ] Error handling
- [ ] Configuration compatibility
- [ ] Test coverage

### 📝 Review Checklist

- [ ] Code follows project standards
- [ ] Tests are comprehensive
- [ ] Documentation is complete
- [ ] Security considerations addressed
- [ ] Performance impact acceptable 