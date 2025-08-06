#!/usr/bin/env python3
"""
Migration script to add project support to Keepstone
This script will:
1. Create the project table
2. Add project_id column to artifact table
3. Create a default project
4. Assign all existing artifacts to the default project
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import yaml
import os
import sys

def load_config():
    """Load configuration from config.yaml"""
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        print("Error: config.yaml not found")
        sys.exit(1)
        
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def migrate_to_projects():
    """Run the migration"""
    print("Starting migration to add project support...")
    
    # Load config
    config = load_config()
    
    # Create database connection
    db_path = f"{config['sql_alchemy']['loc']}/{config['sql_alchemy']['db']}"
    engine = create_engine(f'sqlite:///{db_path}')
    
    with engine.connect() as conn:
        print("Connected to database")
        
        # 1. Create project table
        print("Creating project table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 2. Add project_id column to artifact table
        print("Adding project_id column to artifact table...")
        try:
            conn.execute(text("""
                ALTER TABLE artifact 
                ADD COLUMN project_id INTEGER REFERENCES project(id)
            """))
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("project_id column already exists, skipping...")
            else:
                raise e
        
        # 3. Create default project if it doesn't exist
        print("Creating default project...")
        result = conn.execute(text("SELECT COUNT(*) FROM project WHERE name = 'Default'"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO project (name, description, is_default, created_at)
                VALUES ('Default', 'Default project for existing artifacts', TRUE, CURRENT_TIMESTAMP)
            """))
            print("Default project created")
        else:
            print("Default project already exists")
        
        # 4. Get the default project ID
        result = conn.execute(text("SELECT id FROM project WHERE name = 'Default'"))
        default_project_id = result.scalar()
        
        # 5. Assign all artifacts without a project to the default project
        print("Assigning existing artifacts to default project...")
        result = conn.execute(text("""
            UPDATE artifact 
            SET project_id = :project_id 
            WHERE project_id IS NULL
        """), {"project_id": default_project_id})
        
        updated_count = result.rowcount
        print(f"Updated {updated_count} artifacts to use default project")
        
        # 6. Add default project config if it doesn't exist
        print("Adding default project configuration...")
        try:
            conn.execute(text("""
                INSERT OR IGNORE INTO config (key, value, description)
                VALUES ('ui.default_project_id', :project_id, 'Default project ID for new artifacts')
            """), {"project_id": str(default_project_id)})
        except Exception as e:
            print(f"Note: Could not add default project config: {e}")
        
        # Commit all changes
        conn.commit()
        print("Migration completed successfully!")

def rollback_migration():
    """Rollback the migration (for testing purposes)"""
    print("Rolling back project migration...")
    
    config = load_config()
    db_path = f"{config['sql_alchemy']['loc']}/{config['sql_alchemy']['db']}"
    engine = create_engine(f'sqlite:///{db_path}')
    
    with engine.connect() as conn:
        # Note: SQLite doesn't support DROP COLUMN, so we can't fully rollback
        print("Warning: SQLite doesn't support DROP COLUMN")
        print("To fully rollback, you would need to:")
        print("1. Create a new table without project_id")
        print("2. Copy data from old table")
        print("3. Drop old table and rename new table")
        print("4. Drop project table")
        
        # We can at least drop the project table and clear project_id values
        conn.execute(text("UPDATE artifact SET project_id = NULL"))
        conn.execute(text("DROP TABLE IF EXISTS project"))
        conn.execute(text("DELETE FROM config WHERE key = 'ui.default_project_id'"))
        conn.commit()
        print("Partial rollback completed")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback_migration()
    else:
        migrate_to_projects()
