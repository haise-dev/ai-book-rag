#!/usr/bin/env python3
"""
Quick database check script for PostgreSQL in Docker
"""

import os
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

def check_database():
    """Quick check of database status and contents"""
    
    # Connection parameters
    conn_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    print("PostgreSQL Database Status Check")
    print("=" * 50)
    print(f"Host: {conn_params['host']}:{conn_params['port']}")
    print(f"Database: {conn_params['database']}")
    print(f"User: {conn_params['user']}")
    print("=" * 50)
    
    try:
        # Connect
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print("✓ Connection successful!")
        
        # Get all tables
        cur.execute("""
            SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name::regclass)) as size
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        if tables:
            print(f"\nFound {len(tables)} tables:")
            print(tabulate(tables, headers=['Table Name', 'Size'], tablefmt='grid'))
            
            # Get row counts for each table
            print("\nRow counts:")
            row_counts = []
            for table_name, _ in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cur.fetchone()[0]
                row_counts.append([table_name, count])
            
            print(tabulate(row_counts, headers=['Table', 'Rows'], tablefmt='grid'))
        else:
            print("\nNo tables found in database!")
        
        # Close connection
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    check_database()
