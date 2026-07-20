import sys
sys.path.insert(0, r'c:\Users\ASUS\OneDrive\Desktop\AI DATA ANALYST\ai-data-analyst\backend')
from app.config import DATABASE_URL
from sqlalchemy import create_engine, text

e = create_engine(DATABASE_URL)
with e.connect() as conn:
    print('engine url:', e.url)
    r = conn.execute(text("select current_user, session_user, current_database(), current_schema(), current_schemas(true), current_setting('search_path')")).fetchone()
    print('user/session/db/schema/search_path:', r)

    for t in ('uploaded_files','database_connections'):
        print('\n---', t)
        try:
            print('has_table_privilege SELECT (unqualified):', conn.execute(text("select has_table_privilege(current_user, :t, 'SELECT')"), {'t': t}).scalar())
        except Exception as ex:
            print('has_table_privilege unqualified error:', ex)
        try:
            print("has_table_privilege 'public.%s':" % t, conn.execute(text("select has_table_privilege(current_user, :fq, 'SELECT')"), {'fq': f'public.{t}'}).scalar())
        except Exception as ex:
            print('has_table_privilege public qualified error:', ex)
        try:
            rows = conn.execute(text("select grantee, privilege_type from information_schema.role_table_grants where table_name = :t"), {'t': t}).fetchall()
            print('role_table_grants:')
            for r in rows:
                print(' ', r)
        except Exception as ex:
            print('role_table_grants error:', ex)
        try:
            rows = conn.execute(text("select relname, relacl from pg_class where relname = :t"), {'t': t}).fetchall()
            print('pg_class relacl:', rows)
        except Exception as ex:
            print('pg_class error:', ex)
