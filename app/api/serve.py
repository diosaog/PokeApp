"""Hosted API entry point. Fail closed when required server configuration is absent."""
from __future__ import annotations

import os

from app.api.config import APIConfig


def main() -> None:
    config = APIConfig.from_env()
    if not all((config.supabase_url.startswith('https://'), config.supabase_anon_key,
                config.supabase_service_role_key, config.auth_pin_pepper,
                config.cors_origins)):
        raise SystemExit('Missing required API server configuration; refusing startup.')
    port = int(os.environ.get('PORT', '8000'))
    if not 1 <= port <= 65535:
        raise SystemExit('Invalid API port.')
    import uvicorn
    # One process/replica while the PIN limiter remains in-memory. Untrusted
    # Forwarded/X-Forwarded-For headers must not bypass that limiter.
    uvicorn.run('app.api.main:app', host='0.0.0.0', port=port,
                workers=1, proxy_headers=False)


if __name__ == '__main__':
    main()
