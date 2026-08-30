from azure.appconfiguration.provider import load, SettingSelector
from azure.identity import DefaultAzureCredential
import os
from typing import Any

_config = None

def initialize() -> None:
    global _config

    if _config is not None:
        return

    credential = DefaultAzureCredential()
    endpoint = os.environ["az_appconfig_endpoint"]

    _config = load(
        endpoint=endpoint,
        credential=credential,
        keyvault_credential=credential,
        trim_prefixes=["data:", "parsing:"]
    )

    # Debug: print all loaded keys to help diagnose missing keys
    loaded_keys = list(_config.keys())
    print(f"[config] Loaded {len(loaded_keys)} keys from App Configuration: {loaded_keys}")

    # Expose all config values as env vars so Azure Functions
    # can resolve trigger/output binding connections at startup
    for key, value in _config.items():
        os.environ[key] = str(value)

def get_key(key: str) -> Any:
    try:
        value = _config[key]
        return value
    except KeyError:
        # Debug: print available keys to help diagnose
        if _config is not None:
            available_keys = list(_config.keys())
            raise RuntimeError(f"missing key '{key}'. Available keys: {available_keys}")
        raise RuntimeError(f"missing key '{key}'. Config not initialized.")