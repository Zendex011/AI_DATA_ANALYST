import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    database="ai_data_analyst",
    user="ai_data_analyst",
    password="MEERUT1234",
)

print("CONNECTED!")
conn.close()