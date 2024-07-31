import streamlit as st
from llm_chains import load_normal_chain, load_pdf_chat_chain
from streamlit_mic_recorder import mic_recorder
from utils import get_timestamp, load_config, get_avatar
from image_handler import handle_image
from audio_handler import transcribe_audio
from pdf_handler import add_documents_to_db
from html_templates import css
from database_operations import load_last_k_text_messages, save_text_message, save_image_message, save_audio_message, load_messages, get_all_chat_history_ids, delete_chat_history, get_db_connection_and_cursor, add_user, validate_user
import sqlite3

config = load_config()

@st.cache_resource
def load_chain():
    if st.session_state.pdf_chat:
        print("loading pdf chat chain")
        return load_pdf_chat_chain()
    return load_normal_chain()

def toggle_pdf_chat():
    st.session_state.pdf_chat = True
    clear_cache()


def get_user_id(username):
    conn, cursor = get_db_connection_and_cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()
    if user_id is None:
        cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        user_id = cursor.lastrowid
    else:
        user_id = user_id[0]
    return user_id

def get_session_key():
    if st.session_state.session_key == "new_session":
        st.session_state.new_session_key = f"{get_timestamp()}_{st.session_state.user}"
        return st.session_state.new_session_key
    return st.session_state.session_key

def delete_chat_session_history():
    delete_chat_history(st.session_state.session_key)
    st.session_state.session_index_tracker = "new_session"

def clear_cache():
    st.cache_resource.clear()
    
def main():
    st.title("StudyBot")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        show_main_app()
    else:
        show_login_signup()

def show_login_signup():
    st.sidebar.title("Welcome to StudyBot")
    
    choice = st.sidebar.selectbox("Login/Signup", ["Login", "Signup"])
    
    if choice == "Signup":
        username = st.sidebar.text_input("Username")
        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Signup"):
            if add_user(username, email, password):
                st.success("User created successfully!")
            else:
                st.error("Username already exists. Try a different one.")
    
    if choice == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if validate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                conn, cursor = get_db_connection_and_cursor()
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                user = cursor.fetchone()[0]
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

def show_main_app():
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'session_key' not in st.session_state:
        st.session_state.session_key = "new_session"
    if 'new_session_key' not in st.session_state:
        st.session_state.new_session_key = None
    if 'session_index_tracker' not in st.session_state:
        st.session_state.session_index_tracker = "new_session"
    if 'audio_uploader_key' not in st.session_state:
        st.session_state.audio_uploader_key = 0
    if 'pdf_uploader_key' not in st.session_state:
        st.session_state.pdf_uploader_key = 1

    if st.session_state.session_key == "new_session" and st.session_state.new_session_key is not None:
        st.session_state.session_index_tracker = st.session_state.new_session_key
        st.session_state.new_session_key = None
    
    st.markdown(f"<h3 style='text-align: left;'>Welcome, {st.session_state.username}</h3>", unsafe_allow_html=True)
    st.write(css, unsafe_allow_html=True)
    
    if "db_conn" not in st.session_state:
        st.session_state.db_conn = sqlite3.connect(config["chat_sessions_database_path"], check_same_thread=False)
    
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.sidebar.title("Chat Sessions")
    chat_sessions = ["new_session"] + get_all_chat_history_ids()

    #Ensure the current session is in the list of chat sessions
    if st.session_state.session_index_tracker not in chat_sessions:
        chat_sessions.append(st.session_state.session_index_tracker)

    index = chat_sessions.index(st.session_state.session_index_tracker)
    st.sidebar.selectbox("Select a chat session", chat_sessions, key="session_key", index=index)
    pdf_toggle_col, voice_rec_col = st.sidebar.columns(2)
    pdf_toggle_col.toggle("PDF Chat", key="pdf_chat", value=False, on_change=clear_cache)
    #with voice_rec_col:
      #  voice_recording=mic_recorder(start_prompt="Record Audio",stop_prompt="Stop recording", just_once=True)
    delete_chat_col, clear_cache_col = st.sidebar.columns(2)
    delete_chat_col.button("Delete Chat Session", on_click=delete_chat_session_history)
    clear_cache_col.button("Clear Cache", on_click=clear_cache)
    
    chat_container = st.container()
    user_input = st.chat_input("Type your message here", key="user_input")
    
    uploaded_audio = st.sidebar.file_uploader("Upload an audio file", type=["wav", "mp3", "ogg"], key=st.session_state.audio_uploader_key)
    uploaded_image = st.sidebar.file_uploader("Upload an image file", type=["jpg", "jpeg", "png"])
    uploaded_pdf = st.sidebar.file_uploader("Upload a pdf file", accept_multiple_files=True, 
                                            key=st.session_state.pdf_uploader_key, type=["pdf"], on_change=toggle_pdf_chat)

    if uploaded_pdf:
        with st.spinner("Processing pdf..."):
            add_documents_to_db(uploaded_pdf)
            st.session_state.pdf_uploader_key += 2

   # if uploaded_audio:
   #     transcribed_audio = transcribe_audio(uploaded_audio.getvalue())
   #     print(transcribed_audio)
   #     llm_chain = load_chain()
    #    llm_answer = llm_chain.run(user_input = "Summarize this text: " + transcribed_audio, chat_history=[])
   #     save_audio_message(get_session_key(), "human", uploaded_audio.getvalue())
   #    save_text_message(get_session_key(), "ai", llm_answer)
    #    st.session_state.audio_uploader_key += 2

   # if voice_recording:
     #   transcribed_audio = transcribe_audio(voice_recording["bytes"])
      #  print(transcribed_audio)
      #  llm_chain = load_chain()
       # llm_answer = llm_chain.run(user_input = transcribed_audio, 
                #                   chat_history=load_last_k_text_messages(get_session_key(), config["chat_config"]["chat_memory_length"]))
      #  save_audio_message(get_session_key(), "human", voice_recording["bytes"])
        #save_text_message(get_session_key(), "ai", llm_answer)

    
    if user_input:
        if uploaded_image:
            with st.spinner("Processing image..."):
                llm_answer = handle_image(uploaded_image.getvalue(), user_input)
                save_text_message(get_session_key(), st.session_state.user,"human", user_input)
                save_image_message(get_session_key(), st.session_state.user,"human", uploaded_image.getvalue())
                save_text_message(get_session_key(), st.session_state.user,"ai", llm_answer)
                
        elif uploaded_audio:
            transcribed_audio = transcribe_audio(uploaded_audio.getvalue())
            print(transcribed_audio)
            save_text_message(get_session_key(), st.session_state.user, "human", user_input)  # Save user input message
            save_audio_message(get_session_key(), st.session_state.user, "human", uploaded_audio.getvalue())  # Save uploaded audio
            save_text_message(get_session_key(), st.session_state.user, "ai", transcribed_audio)  # Save transcribed audio as AI response
            llm_chain = load_chain()
            #llm_answer = llm_chain.run(user_input="Summarize this text: " + transcribed_audio, chat_history=[])
            #save_text_message(get_session_key(), st.session_state.user, "ai", llm_answer)  # Save LLM response
            st.session_state.audio_uploader_key += 2
        else:
            llm_chain = load_chain()
            llm_answer = llm_chain.run(user_input=user_input, 
                                       chat_history=load_last_k_text_messages(get_session_key(), config["chat_config"]["chat_memory_length"]))
            save_text_message(get_session_key(), st.session_state.user,"human", user_input)
            save_text_message(get_session_key(), st.session_state.user, "ai", llm_answer)

    if (st.session_state.session_key != "new_session") != (st.session_state.new_session_key != None):
        with chat_container:
            chat_history_messages = load_messages(get_session_key(),st.session_state.user)

            for message in chat_history_messages:
                with st.chat_message(name=message["sender_type"], avatar=get_avatar(message["sender_type"])):
                    if message["message_type"] == "text":
                        st.write(message["content"])
                    if message["message_type"] == "image":
                        st.image(message["content"])
                    if message["message_type"] == "audio":
                        st.audio(message["content"], format="audio/wav")

        if (st.session_state.session_key == "new_session") and (st.session_state.new_session_key != None):
            st.rerun()

if __name__ == "__main__":
    main()