from pathlib import Path

import yaml

from helpers.sv_config import validate_config

server_data = "data/servers"

class ConfigService:
    """A WIP config service that caches the server config data in memory. Eventually,
    all calls to config.yml will come through this class."""
    def __init__(self):
        self.server_configs = self.load_server_configs()

    def get_server_config(self, server_id: int, section: str, field: str):
        """Fetches a field value from the cached server config, if it exists.
        Args:
            server_id: The discord server ID to fetch the config for
            section: The top-level config section (e.g. "staff", "toss", "reaction")
            field: The field within the section (e.g. "modrole", "tossrole")

        Returns:
            The value of the field, or None if the guild, section, or field does not exist.
        """
        if server_id not in self.server_configs:
            return None

        server_config = self.server_configs[server_id]
        if section not in server_config:
            return None

        section_config = server_config[section]
        return section_config[field] if field in section_config else None

    def reload_configs(self):
        """Internally reloads the server config cache from disk"""
        self.server_configs = self.load_server_configs()

    def load_server_configs(self):
        """Fetches all server configs for this bot.

        Returns:
            dict where the key is the server ID and the value is the config dict for that server
        """
        server_configs = {}
        for server_dir in Path(server_data).iterdir():
            if server_dir.is_dir():
                server_id = server_dir.name
                if server_id is None:
                    continue

                server_config = None
                try:
                    with open(server_dir / "config.yml", "r") as file:
                        server_config = yaml.safe_load(file)
                except FileNotFoundError:
                    continue

                validate_config(server_config)

                server_configs[int(server_id)] = server_config

        return server_configs