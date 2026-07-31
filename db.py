import os
import time

import httpx
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(postgrest_client_timeout=30),
)

TRANSIENT_ERRNOS = {11, 104, 110}  # EAGAIN, ECONNRESET, ETIMEDOUT


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, OSError):
        return exc.errno in TRANSIENT_ERRNOS
    return False


def execute(builder, retries: int = 3, backoff: float = 0.3):
    for attempt in range(retries):
        try:
            return builder.execute()
        except Exception as e:
            if not _is_transient(e) or attempt == retries - 1:
                raise
            time.sleep(backoff * (2 ** attempt))
