import sys
import os
from pathlib import Path
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

try:
    print(f"Connecting to {config['host']}:{config['port']}/{config['database']} as {config['user']}...")
    connection = pymysql.connect(**config)
    
    with connection.cursor() as cursor:
    
        cursor.execute("SELECT COUNT(*) FROM plans")
        count = cursor.fetchone()[0]
        
        if count >= 2:
            print(f"Found {count} plans, skipping")
            sys.exit(0)
        
        
        print("Inserting plans...")
        cursor.execute("""
            INSERT INTO plans (slug, name, description, base_price)
            VALUES ('basic', 'Basic', 'Basic OHS manual', 99.99)
        """)
        
        cursor.execute("""
            INSERT INTO plans (slug, name, description, base_price)
            VALUES ('comprehensive', 'Comprehensive', 'Comprehensive OHS manual', 199.99)
        """)
        
        connection.commit()
        
        print("Plans inserted successfully")
        
    
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