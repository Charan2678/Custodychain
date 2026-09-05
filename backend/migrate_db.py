from database import engine, Base
import models
from sqlalchemy import text

def run_migration():
    print("Checking database tables and columns...")
    # 1. Create all missing tables (users, cases, artifacts, custody_events, audit_events)
    Base.metadata.create_all(bind=engine)
    print("Ensured all tables exist.")

    # 2. Check and add missing columns to evidence table
    with engine.connect() as conn:
        res = conn.execute(text("DESCRIBE evidence;"))
        cols = [r[0] for r in res.fetchall()]
        print("Current evidence columns:", cols)

        alter_statements = []
        if "case_id" not in cols:
            alter_statements.append("ALTER TABLE evidence ADD COLUMN case_id INT NULL;")
        if "exhibit_id" not in cols:
            alter_statements.append("ALTER TABLE evidence ADD COLUMN exhibit_id VARCHAR(50) NULL;")
        if "media_type" not in cols:
            alter_statements.append("ALTER TABLE evidence ADD COLUMN media_type VARCHAR(100) DEFAULT 'text/plain';")
        if "size_bytes" not in cols:
            alter_statements.append("ALTER TABLE evidence ADD COLUMN size_bytes INT DEFAULT 0;")
        if "status" not in cols:
            alter_statements.append("ALTER TABLE evidence ADD COLUMN status VARCHAR(30) DEFAULT 'VERIFIED';")
        if "created_by" not in cols:
            alter_statements.append("ALTER TABLE evidence ADD COLUMN created_by VARCHAR(100) DEFAULT 'Charan';")

        for stmt in alter_statements:
            print("Executing:", stmt)
            conn.execute(text(stmt))
        conn.commit()
        print("Migration finished successfully!")

if __name__ == "__main__":
    run_migration()
