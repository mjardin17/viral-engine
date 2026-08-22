#!/usr/bin/env python3
"""Execute SQL migration directly via Postgres"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Connect to Postgres database directly
try:
    conn = psycopg2.connect(
        host="db.irslzufsqjveyibkfjtz.supabase.co",
        database="postgres",
        user="postgres.irslzufsqjveyibkfjtz",
        password=os.getenv("SUPABASE_DB_PASSWORD", "Bullet173169!"),
        port=5432,
        sslmode="require",
    )
    cursor = conn.cursor()

    print("Executing SQL grant...")
    cursor.execute("GRANT SELECT ON public.products TO service_role;")
    cursor.execute("GRANT UPDATE ON public.products TO service_role;")
    conn.commit()

    print("✓ Permissions granted to service_role")
    cursor.close()
    conn.close()

except psycopg2.Error as e:
    print(f"ERROR: {e}")
    print("\nAlternative: Go to Supabase Dashboard > SQL Editor and run:")
    print("GRANT SELECT ON public.products TO service_role;")
    print("GRANT UPDATE ON public.products TO service_role;")
    sys.exit(1)
