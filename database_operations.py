import streamlit as st
import sqlite3
import os
from utils import load_config

config = load_config()

def get_db_connection():
    if 'db_conn' not in st.session_state or st.session_state.db_conn is None:
        st.session_state.db_conn = sqlite3.connect(config["chat_sessions_database_path"], check_same_thread=False)
    return st.session_state.db_conn

def get_db_cursor(db_connection):
    return db_connection.cursor()

def get_db_connection_and_cursor():
    conn = get_db_connection()
    return conn, conn.cursor()

def close_db_connection():
    if 'db_conn' in st.session_state and st.session_state.db_conn is not None:
        st.session_state.db_conn.close()
        st.session_state.db_conn = None
def add_user(username, email, password):
    conn, cursor = get_db_connection_and_cursor()
    try:
        cursor.execute('INSERT INTO users (username, Email, password) VALUES (?,?, ?)', (username, email, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
def validate_user(username, password):
    conn, cursor = get_db_connection_and_cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    return cursor.fetchone() is not None

def save_text_message(chat_history_id, user, sender_type, text):
    conn, cursor = get_db_connection_and_cursor()
    cursor.execute('INSERT INTO messages (chat_history_id, user, sender_type, message_type, text_content) VALUES (?, ?, ?, ?, ?)',
                   (chat_history_id, user, sender_type, 'text', text))
    conn.commit()

def save_image_message(chat_history_id, user, sender_type, image_bytes):
    conn, cursor = get_db_connection_and_cursor()
    cursor.execute('INSERT INTO messages (chat_history_id, user, sender_type, message_type, blob_content) VALUES (?, ?, ?, ?, ?)',
                   (chat_history_id, user, sender_type, 'image', sqlite3.Binary(image_bytes)))
    conn.commit()

def save_audio_message(chat_history_id, user, sender_type, audio_bytes):
    conn, cursor = get_db_connection_and_cursor()
    cursor.execute('INSERT INTO messages (chat_history_id, user, sender_type, message_type, blob_content) VALUES (?, ?, ?, ?, ?)',
                   (chat_history_id, user, sender_type, 'audio', sqlite3.Binary(audio_bytes)))
    conn.commit()

def load_messages(chat_history_id, user):
    conn, cursor = get_db_connection_and_cursor()
    query = "SELECT message_id, sender_type, message_type, text_content, blob_content FROM messages WHERE chat_history_id = ? AND user = ?"
    cursor.execute(query, (chat_history_id, user))
    messages = cursor.fetchall()
    chat_history = []
    for message in messages:
        message_id, sender_type, message_type, text_content, blob_content = message
        if message_type == 'text':
            chat_history.append({'message_id': message_id, 'sender_type': sender_type, 'message_type': message_type, 'content': text_content})
        else:
            chat_history.append({'message_id': message_id, 'sender_type': sender_type, 'message_type': message_type, 'content': blob_content})
    return chat_history
def load_last_k_text_messages(chat_history_id, k):
    conn, cursor = get_db_connection_and_cursor()
    query = """
    SELECT message_id, sender_type, message_type, text_content
    FROM messages
    WHERE chat_history_id = ? AND message_type = 'text'
    ORDER BY message_id DESC
    LIMIT ?
    """
    cursor.execute(query, (chat_history_id, k))
    messages = cursor.fetchall()
    chat_history = []
    for message in reversed(messages):
        message_id, sender_type, message_type, text_content = message
        chat_history.append({
            'message_id': message_id,
            'sender_type': sender_type,
            'message_type': message_type,
            'content': text_content
        })
    return chat_history
def get_all_chat_history_ids():
    conn, cursor = get_db_connection_and_cursor()
    query = "SELECT DISTINCT chat_history_id FROM messages ORDER BY chat_history_id ASC"
    cursor.execute(query)
    chat_history_ids = cursor.fetchall()
    chat_history_id_list = [item[0] for item in chat_history_ids]
    return chat_history_id_list

def delete_chat_history(chat_history_id):
    conn, cursor = get_db_connection_and_cursor()
    query = "DELETE FROM messages WHERE chat_history_id = ?"
    cursor.execute(query, (chat_history_id,))
    conn.commit()
    print(f"All entries with chat_history_id {chat_history_id} have been deleted.")

def init_db():
    db_path = config["chat_sessions_database_path"]
    print(f"Initializing database at path: {db_path}")

    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("Database connection established.")
        
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            Email VARCHAR(255) UNIQUE,
            password TEXT NOT NULL
        );
        """

        create_messages_table = """
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_history_id TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            message_type TEXT NOT NULL,
            text_content TEXT,
            blob_content BLOB,
            user INTEGER NOT NULL,
            FOREIGN KEY (user) REFERENCES users(user_id)
        );
        """

        cursor.execute(create_messages_table)
        cursor.execute(create_users_table)
        conn.commit()
        print("Tables creation command executed.")

        # Debug: Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'  AND name='messages';")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'  AND name='users';")
        table_exists = cursor.fetchone()
        if table_exists:
            print("Table 'messages' and 'users' exists.")
        else:
            print("Table 'messages' or 'users' does not exist or both.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

# Initialize the database when the app starts
init_db()

# Streamlit app code
st.title("Chat Application")
# Your additional Streamlit app code goes here

# Example Streamlit app content
if st.button("Show all chat history IDs"):
    chat_history_ids = get_all_chat_history_ids()
    st.write(chat_history_ids)

