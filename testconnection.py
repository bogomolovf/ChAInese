import psycopg2
from psycopg2 import sql
import os

# Database URL (update with your Supabase credentials)
DATABASE_URL = "postgresql://postgres.uilrtenermvclsnjlcym:goodgame2254FF@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

def test_connection():
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(DATABASE_URL)

        # Создание курсора для выполнения операций
        cursor = connection.cursor()

        # Выполняем простой SQL-запрос
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        print("Connection successful:", result[0])

    except Exception as e:
        print("Error connecting to the database:", e)

    finally:
        # Закрытие соединения
        if connection:
            cursor.close()
            connection.close()
            print("Connection closed.")

def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                context TEXT NOT NULL
            )
            """
        )

        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Add a flashcard
def add_flashcard(user_id, word, context):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            sql.SQL(
                """
                INSERT INTO flashcards (user_id, word, context)
                VALUES (%s, %s, %s)
                """
            ),
            (user_id, word, context)
        )

        conn.commit()
        cur.close()
        conn.close()
        print(f"Flashcard added successfully: {word} - {context}")
    except Exception as e:
        print(f"Error adding flashcard: {e}")

# Main function to interact with the terminal
def main():
    # Initialize the database
    init_db()

    while True:
        print("\n--- Flashcard Management ---")
        print("1. Add a new flashcard")
        print("2. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            user_id = input("Enter user ID (integer): ").strip()
            word = input("Enter the word: ").strip()
            context = input("Enter the context or example sentence: ").strip()

            # Validate inputs
            if not user_id.isdigit():
                print("Invalid user ID. Please enter an integer.")
                continue

            if not word or not context:
                print("Word and context cannot be empty. Try again.")
                continue

            # Add flashcard
            add_flashcard(int(user_id), word, context)

        elif choice == "2":
            print("Exiting Flashcard Management. Goodbye!")
            break
        else:
            print("Invalid choice. Please select a valid option.")

# Entry point
if __name__ == "__main__":
    main()







