import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql


config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': 'root_password',
    'database': 'ohs_remote_dev',
    'charset': 'utf8mb4'
}

try:
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
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'connection' in locals():
        connection.close()