import os
import yaml
from loguru import logger
from typing import Dict, Any
from .const import DATA_DIR


CONFIGURATION_VERSION = 1
CONFIG_FILE_PATH = os.path.join(DATA_DIR, f"config_v{CONFIGURATION_VERSION}.yaml")

class ConfigPersistence:
    def __init__(self, default_config: Dict[str, Any]):
        self.default_config = default_config
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        os.makedirs(DATA_DIR, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load configuration from file or return default if not found."""
        try:
            if os.path.exists(CONFIG_FILE_PATH):
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as file:
                    config_data = yaml.safe_load(file)
                    if config_data:
                        return config_data
        except (yaml.YAMLError, AssertionError) as e:
            logger.error(f"Error loading config file: {e}")
        return self.default_config

    def save(self, config_data: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as file:
                yaml.safe_dump(config_data, file, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
        except IOError as e:
            logger.error(f"Error saving config file: {e}")
            return False

    def update_section(self, section_name: str, section_data: Any) -> bool:
        """Update a specific section of the configuration."""
        config_data = self.load()
        config_data[section_name] = section_data
        return self.save(config_data)

    def delete_section(self, section_name: str) -> bool:
        """Delete a specific section from the configuration."""
        config_data = self.load()
        if section_name in config_data:
            del config_data[section_name]
            return self.save(config_data)
        return False 
