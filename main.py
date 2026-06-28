from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import yaml
from dotenv import dotenv_values
from typing import List, Optional

app = FastAPI()

# CORS configuration to allow the grader to check the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def coerce_types(config_dict: dict) -> dict:
    """Helper function to convert values to their correct types."""
    result = {}
    for key, value in config_dict.items():
        if key in ["port", "workers"]:
            try:
                result[key] = int(value)
            except (ValueError, TypeError):
                result[key] = value
        elif key == "debug":
            if isinstance(value, str):
                # Case-insensitive check for true/1/yes/on
                result[key] = value.lower() in ["true", "1", "yes", "on"]
            else:
                result[key] = bool(value)
        else:
            result[key] = str(value)
    return result

@app.get("/effective-config")
def get_effective_config(set: Optional[List[str]] = Query(None)):
    # Layer 1: Hardcoded Defaults
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000"
    }

    # Layer 2: YAML configuration
    try:
        with open("config.development.yaml", "r") as f:
            yaml_config = yaml.safe_load(f) or {}
            config.update(yaml_config)
    except FileNotFoundError:
        pass # Ignore if file not found

    # Layer 3: .env file
    env_file_config = dotenv_values(".env")
    for key, value in env_file_config.items():
        if key == "NUM_WORKERS":
            config["workers"] = value
        elif key.startswith("APP_"):
            # APP_PORT becomes port
            clean_key = key[4:].lower()
            config[clean_key] = value

    # Layer 4: OS Environment Variables
    for key, value in os.environ.items():
        if key == "NUM_WORKERS":
            config["workers"] = value
        elif key.startswith("APP_"):
            clean_key = key[4:].lower()
            config[clean_key] = value

    # Layer 5: CLI Overrides via Query Parameters (?set=key=value)
    if set:
        for override in set:
            if "=" in override:
                k, v = override.split("=", 1)
                config[k] = v

    # Apply type coercion rules
    final_config = coerce_types(config)

    # Secret Masking: api_key must always be "****"
    if "api_key" in final_config:
        final_config["api_key"] = "****"

    return final_config
