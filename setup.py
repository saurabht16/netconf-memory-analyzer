#!/usr/bin/env python3
"""
Setup configuration for NETCONF Memory Leak Analyzer
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open('requirements.txt') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            # Remove version specifiers for setup.py
            req = line.split('>=')[0].split('==')[0].split('<=')[0]
            requirements.append(req)

setup(
    name="netconf-memory-analyzer",
    version="1.0.0",
    author="NETCONF Memory Analyzer Team",
    author_email="your.email@example.com",
    description="Comprehensive memory leak testing and analysis for containerized NETCONF applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/netconf-memory-analyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "gui": ["tkinter-tooltip"],
        "plotting": ["matplotlib", "plotly"],
        "dev": ["pytest", "pytest-cov", "black", "flake8"],
        "docs": ["sphinx", "sphinx-rtd-theme"],
    },
    entry_points={
        "console_scripts": [
            "netconf-memory-test=parallel_device_tester:main",
            "netconf-memory-analyze=memory_leak_analyzer_enhanced:main",
            "netconf-memory-gui=memory_leak_analyzer:main",
            "netconf-complete-analysis=complete_device_analysis:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml", "test_data/*.xml", "test_data/*.log"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/netconf-memory-analyzer/issues",
        "Source": "https://github.com/yourusername/netconf-memory-analyzer",
        "Documentation": "https://github.com/yourusername/netconf-memory-analyzer/wiki",
    },
) 