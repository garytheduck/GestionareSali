from app import create_app, db
import sqlite3
import os

app = create_app()

def get_db_path():
    """Get the path to the SQLite database file"""
    with app.app_context():
        # Extract the path from the DATABASE_URL
        db_url = app.config['SQLALCHEMY_DATABASE_URL']
        if db_url.startswith('sqlite:///'):
            # Remove the sqlite:/// prefix
            db_path = db_url[10:]
            # If it's a relative path, make it absolute
            if not os.path.isabs(db_path):
                db_path = os.path.join(app.root_path, db_path)
            return db_path
        else:
            return None

def show_tables_schema():
    """Show the schema of all tables in the database"""
    db_path = get_db_path()
    
    if not db_path or not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        # Try to find the database file in the app directory
        app_dir = os.path.dirname(os.path.abspath(__file__))
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                if file.endswith('.db'):
                    db_path = os.path.join(root, file)
                    print(f"Found database at {db_path}")
                    break
            if db_path and os.path.exists(db_path):
                break
    
    if not db_path or not os.path.exists(db_path):
        print("Could not find the database file. Please check your configuration.")
        return
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return
        
        print(f"Found {len(tables)} tables in the database:")
        
        # For each table, get its schema
        for table in tables:
            table_name = table[0]
            print(f"\n{'=' * 50}")
            print(f"TABLE: {table_name}")
            print(f"{'=' * 50}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            if not columns:
                print("No columns found for this table.")
                continue
            
            # Print column information
            print(f"{'Column Name':<20} {'Type':<15} {'Not Null':<10} {'Default':<15} {'Primary Key'}")
            print(f"{'-' * 20} {'-' * 15} {'-' * 10} {'-' * 15} {'-' * 11}")
            
            for column in columns:
                col_id, name, type_, not_null, default_val, pk = column
                print(f"{name:<20} {type_:<15} {'Yes' if not_null else 'No':<10} {str(default_val):<15} {'Yes' if pk else 'No'}")
            
            # Get foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            foreign_keys = cursor.fetchall()
            
            if foreign_keys:
                print("\nForeign Keys:")
                print(f"{'Column':<20} {'References':<30} {'On Delete':<15} {'On Update'}")
                print(f"{'-' * 20} {'-' * 30} {'-' * 15} {'-' * 9}")
                
                for fk in foreign_keys:
                    id_, seq, table, from_, to, on_update, on_delete, match = fk
                    print(f"{from_:<20} {table + '.' + to:<30} {on_delete:<15} {on_update}")
            
            # Get indexes
            cursor.execute(f"PRAGMA index_list({table_name});")
            indexes = cursor.fetchall()
            
            if indexes:
                print("\nIndexes:")
                for idx in indexes:
                    idx_name = idx[1]
                    is_unique = "Unique" if idx[2] else "Not Unique"
                    print(f"{idx_name} ({is_unique})")
                    
                    # Get columns in this index
                    cursor.execute(f"PRAGMA index_info({idx_name});")
                    idx_columns = cursor.fetchall()
                    columns_str = ", ".join([col[2] for col in idx_columns])
                    print(f"  Columns: {columns_str}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    with app.app_context():
        # Alternative method using SQLAlchemy metadata
        print("\nSQLAlchemy Metadata Tables:")
        print("=" * 50)
        
        for table_name in db.metadata.tables.keys():
            table = db.metadata.tables[table_name]
            print(f"\nTABLE: {table_name}")
            print("-" * 50)
            
            # Print columns
            print(f"{'Column Name':<20} {'Type':<30} {'Nullable':<10} {'Default':<15} {'Primary Key'}")
            print(f"{'-' * 20} {'-' * 30} {'-' * 10} {'-' * 15} {'-' * 11}")
            
            for column in table.columns:
                col_name = column.name
                col_type = str(column.type)
                nullable = "No" if not column.nullable else "Yes"
                default = str(column.default) if column.default is not None else "None"
                pk = "Yes" if column.primary_key else "No"
                
                print(f"{col_name:<20} {col_type:<30} {nullable:<10} {default:<15} {pk}")
            
            # Print foreign keys
            if table.foreign_keys:
                print("\nForeign Keys:")
                print(f"{'Column':<20} {'References'}")
                print(f"{'-' * 20} {'-' * 30}")
                
                for fk in table.foreign_keys:
                    col_name = fk.parent.name
                    target = f"{fk.column.table.name}.{fk.column.name}"
                    print(f"{col_name:<20} {target}")
            
            # Print indexes
            if table.indexes:
                print("\nIndexes:")
                for idx in table.indexes:
                    unique = "Unique" if idx.unique else "Not Unique"
                    columns = ", ".join([col.name for col in idx.columns])
                    print(f"{idx.name} ({unique})")
                    print(f"  Columns: {columns}")
    
    # Also show the raw SQLite schema
    print("\n\nRaw SQLite Schema:")
    print("=" * 50)
    show_tables_schema()
