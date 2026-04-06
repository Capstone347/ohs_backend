import sys
import os
from pathlib import Path
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
from urllib.parse import urlparse

database_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root_password@localhost:3307/ohs_remote_dev')

# Replace mysql+pymysql with mysql for urlparse to work
database_url = database_url.replace('mysql+pymysql://', 'mysql://')

parsed = urlparse(database_url)
username = parsed.username or 'root'
password = parsed.password or 'root_password'
hostname = parsed.hostname or 'localhost'
port = parsed.port or 3307
database = parsed.path.lstrip('/') or 'ohs_remote_dev'

config = {
    'host': hostname,
    'port': port,
    'user': username,
    'password': password,
    'database': database,
    'charset': 'utf8mb4'
}

BASIC_PLAN_PRICE = Decimal(os.getenv("BASIC_PLAN_BASE_PRICE", "99.99"))
COMPREHENSIVE_PLAN_PRICE = Decimal(os.getenv("COMPREHENSIVE_PLAN_BASE_PRICE", "199.99"))
INDUSTRY_SPECIFIC_PLAN_PRICE = Decimal(os.getenv("INDUSTRY_SPECIFIC_PLAN_BASE_PRICE", "50.00"))

try:
    print(f"Connecting to {config['host']}:{config['port']}/{config['database']} as {config['user']}...")
    connection = pymysql.connect(**config)
    
    with connection.cursor() as cursor:
    
        print("Ensuring required plans exist...")

        plans_to_seed = [
            ("basic", "Basic", "Basic OHS manual", BASIC_PLAN_PRICE),
            ("comprehensive", "Comprehensive", "Comprehensive OHS manual", COMPREHENSIVE_PLAN_PRICE),
            (
                "industry_specific",
                "Industry Specific",
                "Industry-specific SJP generation for existing manuals",
                INDUSTRY_SPECIFIC_PLAN_PRICE,
            ),
        ]

        inserted = 0
        for slug, name, description, base_price in plans_to_seed:
            cursor.execute("SELECT id FROM plans WHERE slug = %s", (slug,))
            existing = cursor.fetchone()
            if existing:
                continue

            cursor.execute(
                """
                INSERT INTO plans (slug, name, description, base_price)
                VALUES (%s, %s, %s, %s)
                """,
                (slug, name, description, str(base_price)),
            )
            inserted += 1
        
        connection.commit()
        
        print(f"Inserted {inserted} new plan(s)")
        
    
        cursor.execute("SELECT id, slug, name, base_price FROM plans")
        plans = cursor.fetchall()
        print(f"\nPlans in database:")
        for plan in plans:
            print(f"  ID {plan[0]}: '{plan[1]}' / '{plan[2]}' - ${plan[3]}")
            
except pymysql.Error as e:
    print(f"MySQL error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    if 'connection' in locals():
        connection.close()