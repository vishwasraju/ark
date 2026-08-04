import argparse
import os
import sys
import frontmatter
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS okf_nodes (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    type TEXT,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT[],
    source_doc TEXT,
    source_pages TEXT,
    timestamp TIMESTAMPTZ,
    content TEXT NOT NULL,
    topic TEXT,
    search_vec TSVECTOR
);

CREATE INDEX IF NOT EXISTS okf_search_idx ON okf_nodes USING GIN(search_vec);

CREATE OR REPLACE FUNCTION okf_nodes_search_vec_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vec :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.content, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'okf_nodes_search_vec_update'
    ) THEN
        CREATE TRIGGER okf_nodes_search_vec_update
            BEFORE INSERT OR UPDATE ON okf_nodes
            FOR EACH ROW
            EXECUTE FUNCTION okf_nodes_search_vec_trigger();
    END IF;
END;
$$;
"""

def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()

def ingest(path, db_url):
    try:
        conn = psycopg2.connect(db_url)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)
        
    init_db(conn)
    
    md_files = []
    for root, dirs, files in os.walk(path):
        if os.path.abspath(root) == os.path.abspath(path):
            continue
            
        for file in files:
            if file.endswith('.md'):
                if file not in ['index.md', 'log.md']:
                    md_files.append(os.path.join(root, file))
                    
    total_files = len(md_files)
    ingested_count = 0
    
    for i, file_path in enumerate(md_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
            rel_path = os.path.relpath(file_path, path)
            rel_path_no_ext = os.path.splitext(rel_path)[0]
            
            slug = rel_path_no_ext.replace('\\', '/')
            topic = slug.split('/')[0] if '/' in slug else slug
            
            type_val = post.get('type')
            title = post.get('title', '')
            description = post.get('description')
            tags = post.get('tags', [])
            if not isinstance(tags, list):
                tags = [str(tags)] if tags else []
            timestamp = post.get('timestamp')
            
            source = post.get('source', {})
            source_doc = source.get('document') if isinstance(source, dict) else None
            source_pages = str(source.get('pages')) if isinstance(source, dict) and source.get('pages') is not None else None
            
            content = post.content
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO okf_nodes (
                        slug, type, title, description, tags, 
                        source_doc, source_pages, timestamp, content, topic
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (slug) DO UPDATE SET
                        type = EXCLUDED.type,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        tags = EXCLUDED.tags,
                        source_doc = EXCLUDED.source_doc,
                        source_pages = EXCLUDED.source_pages,
                        timestamp = EXCLUDED.timestamp,
                        content = EXCLUDED.content,
                        topic = EXCLUDED.topic
                """, (
                    slug, type_val, title, description, tags,
                    source_doc, source_pages, timestamp, content, topic
                ))
            conn.commit()
            ingested_count += 1
            print(f"[{i}/{total_files}] Ingested: {slug}")
        except Exception as e:
            print(f"[{i}/{total_files}] Error ingesting {file_path}: {e}")
            conn.rollback()
            continue
            
    conn.close()
    print(f"Done! Ingested {ingested_count} nodes into okf_store")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest OKF Markdown files into PostgreSQL")
    parser.add_argument("-p", "--path", required=True, help="Path to OKF folder (e.g., './output (5)')")
    parser.add_argument("--db-url", help="PostgreSQL URL (defaults to env DATABASE_URL or postgresql://okf:okf_secret@localhost:5432/okf_store)")
    
    args = parser.parse_args()
    
    db_url = args.db_url or os.environ.get("DATABASE_URL", "postgresql://okf:okf_secret@localhost:5432/okf_store")
    
    ingest(args.path, db_url)
