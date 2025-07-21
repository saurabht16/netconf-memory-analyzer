"""
Configuration Manager for Memory Leak Analyzer
Supports user preferences, custom cleanup patterns, and analysis settings
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import os

@dataclass
class CleanupConfig:
    """Configuration for cleanup operations"""
    remove_system_libs: bool = True
    remove_third_party: bool = True
    min_leak_size: int = 8
    remove_incomplete_traces: bool = True
    remove_reachable: bool = False
    custom_exclude_patterns: List[str] = None
    
    def __post_init__(self):
        if self.custom_exclude_patterns is None:
            self.custom_exclude_patterns = []

@dataclass 
class FilterConfig:
    """Configuration for filtering operations"""
    default_severity_filter: str = "All"
    auto_filter_small_leaks: bool = False
    auto_filter_system_libs: bool = False
    max_results_display: int = 1000

@dataclass
class ReportConfig:
    """Configuration for report generation"""
    default_format: str = "html"
    include_charts: bool = True
    include_stack_traces: bool = True
    group_similar_by_default: bool = False
    auto_open_reports: bool = False

@dataclass
class AnalysisConfig:
    """Configuration for analysis features"""
    enable_trend_analysis: bool = True
    store_historical_data: bool = True
    auto_categorize_leaks: bool = True
    enable_impact_scoring: bool = True

@dataclass
class AppConfig:
    """Main application configuration"""
    cleanup: CleanupConfig
    filtering: FilterConfig
    reporting: ReportConfig
    analysis: AnalysisConfig
    custom_parsers: List[str] = None
    
    def __post_init__(self):
        if self.custom_parsers is None:
            self.custom_parsers = []

class ConfigManager:
    """Manages application configuration with multiple sources"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.home() / ".memory_leak_analyzer"
        
        self.config_dir = config_dir
        self.config_dir.mkdir(exist_ok=True)
        
        self.config_file = self.config_dir / "config.yaml"
        self.custom_patterns_file = self.config_dir / "custom_patterns.json"
        self.user_presets_file = self.config_dir / "presets.yaml"
        
        self._config = self._load_config()
    
    def _get_default_config(self) -> AppConfig:
        """Get default configuration"""
        return AppConfig(
            cleanup=CleanupConfig(),
            filtering=FilterConfig(),
            reporting=ReportConfig(),
            analysis=AnalysisConfig()
        )
    
    def _load_config(self) -> AppConfig:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = yaml.safe_load(f)
                
                # Parse nested dataclasses
                cleanup_data = data.get('cleanup', {})
                filtering_data = data.get('filtering', {})
                reporting_data = data.get('reporting', {})
                analysis_data = data.get('analysis', {})
                
                return AppConfig(
                    cleanup=CleanupConfig(**cleanup_data),
                    filtering=FilterConfig(**filtering_data),
                    reporting=ReportConfig(**reporting_data),
                    analysis=AnalysisConfig(**analysis_data),
                    custom_parsers=data.get('custom_parsers', [])
                )
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                return self._get_default_config()
        else:
            config = self._get_default_config()
            self.save_config()
            return config
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(asdict(self._config), f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
    
    def get_config(self) -> AppConfig:
        """Get current configuration"""
        return self._config
    
    def update_config(self, **kwargs):
        """Update configuration sections"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save_config()
    
    def load_custom_patterns(self) -> Dict[str, List[str]]:
        """Load custom exclude patterns"""
        if self.custom_patterns_file.exists():
            try:
                with open(self.custom_patterns_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "system_libraries": [],
            "third_party": [],
            "internal_noise": []
        }
    
    def save_custom_patterns(self, patterns: Dict[str, List[str]]):
        """Save custom exclude patterns"""
        try:
            with open(self.custom_patterns_file, 'w') as f:
                json.dump(patterns, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save custom patterns: {e}")
    
    def get_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get user-defined presets"""
        if self.user_presets_file.exists():
            try:
                with open(self.user_presets_file, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        
        return {
            "aggressive_cleanup": {
                "description": "Remove most noise, focus on critical issues",
                "cleanup": {"min_leak_size": 32, "remove_system_libs": True, "remove_reachable": True},
                "filtering": {"default_severity_filter": "HIGH"}
            },
            "conservative": {
                "description": "Keep most leaks, minimal filtering",
                "cleanup": {"min_leak_size": 1, "remove_system_libs": False},
                "filtering": {"default_severity_filter": "All"}
            },
            "development": {
                "description": "Focus on application code, remove external noise",
                "cleanup": {"min_leak_size": 8, "remove_system_libs": True, "remove_third_party": True},
                "filtering": {"auto_filter_system_libs": True}
            }
        }
    
    def apply_preset(self, preset_name: str) -> bool:
        """Apply a configuration preset"""
        presets = self.get_presets()
        if preset_name not in presets:
            return False
        
        preset = presets[preset_name]
        
        # Apply cleanup settings
        if 'cleanup' in preset:
            for key, value in preset['cleanup'].items():
                if hasattr(self._config.cleanup, key):
                    setattr(self._config.cleanup, key, value)
        
        # Apply filtering settings
        if 'filtering' in preset:
            for key, value in preset['filtering'].items():
                if hasattr(self._config.filtering, key):
                    setattr(self._config.filtering, key, value)
        
        self.save_config()
        return True 