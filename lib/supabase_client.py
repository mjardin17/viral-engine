"""Supabase client initialization."""

import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Initialize and return a Supabase client."""
    url = os.getenv("SUPABASE_URL")
    # Try service key first (for writes), fall back to anon key
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and (SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY) must be set in .env"
        )

    return create_client(url, key)
