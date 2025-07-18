import yaml
import shutil
import os
from jsonschema import validate

server_data = "data/servers"
with open("assets/config.example.yml", "r") as f:
    config_stock = yaml.safe_load(f)
with open("assets/config.schema.yml", "r") as f:
    config_schema = yaml.safe_load(f)


def validate_config(config):
    validate(config, config_schema)


def make_config(sid):
    if not os.path.exists(f"{server_data}/{sid}"):
        os.makedirs(f"{server_data}/{sid}")
    shutil.copyfile("assets/config.example.yml", f"{server_data}/{sid}/config.yml")
    return config_stock


def get_config(sid, part, key):
    config = fill_config(sid)

    if part not in config:
        return None

    return config[part][key] if key in config[part] else None


def fill_config(sid):
    config = (
        get_raw_config(sid)
        if os.path.exists(f"{server_data}/{sid}/config.yml")
        else make_config(sid)
    )

    if config["metadata"]["version"] < config_stock["metadata"]["version"]:

        # UPGRADES, PEOPLE! UPGRADES ...

        # Fluff 20 < 21
        if config["metadata"]["version"] < 21:
            config["sticky"] = {"fresh_stickied_threshold": 10}

    validate_config(config)

    return config


def get_raw_config(sid):
    with open(f"{server_data}/{sid}/config.yml", "r") as f:
        config = yaml.safe_load(f)
    return config


def set_raw_config(sid, contents):
    contents["metadata"]["version"] = config_stock["metadata"]["version"]
    with open(f"{server_data}/{sid}/config.yml", "w") as f:
        yaml.dump(contents, f, sort_keys=False)
