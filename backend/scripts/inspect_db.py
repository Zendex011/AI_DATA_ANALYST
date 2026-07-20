import sys
sys.path.insert(0, r'c:\Users\ASUS\OneDrive\Desktop\AI DATA ANALYST\ai-data-analyst\backend')
from app.config import DATABASE_URL
from sqlalchemy import create_engine, text

e = create_engine(DATABASE_URL)
with e.connect() as conn:
    print('engine url:', e.url)
    for t in ('uploaded_files','database_connections'):
        print('\n-- table:', t)
        try:
            rows = conn.execute(text("SELECT column_name, data_type, table_schema FROM information_schema.columns WHERE table_name = :t ORDER BY ordinal_position"), {'t':t}).fetchall()
            for r in rows:
                print(r)
        except Exception as ex:
            print('info_schema error:', ex)
        try:
            print('select zero rows result columns:')
            rs = conn.execute(text(f'SELECT * FROM {t} LIMIT 0'))
            print([c for c in rs.keys()])
        except Exception as ex:
            print('select error:', ex)
