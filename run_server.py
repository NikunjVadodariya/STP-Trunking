#!/usr/bin/env python3
"""
Run SIP Server
"""

import uvicorn
import yaml
from pathlib import Path

# Load config
config_path = Path("config/server_config.yaml")
api_host = "0.0.0.0"
api_port = 8000

if config_path.exists():
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        if config and 'api' in config:
            api_host = config['api'].get('host', api_host)
            api_port = config['api'].get('port', api_port)

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=api_host,
        port=api_port,
        reload=True,
        log_level="info"
    )

