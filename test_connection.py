import psycopg2

def test_connection():
    try:
        connection = psycopg2.connect(
            dbname="postgres",  
            user="rik.vandenberge@ugent.be",    
            password="DBS2024_Ugent",
            host="aws-0-eu-central-1.pooler.supabase.com",
            port="5432",
            sslmode="require"
        )
        print("Verbinding succesvol!")
        connection.close()
    except Exception as error:
        print(f"Fout bij verbinding: {error}")

if __name__ == "__main__":
    test_connection()
