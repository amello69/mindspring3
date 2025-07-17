import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt
import json
import openai
import uuid # For generating unique user IDs if needed

# --- Firebase Initialization ---
# Check if Firebase app is already initialized to prevent re-initialization errors
if not firebase_admin._apps:
    try:
        # Load Firebase service account key from Streamlit secrets
        firebase_service_account_key_str = st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"]['settings']
        cred = credentials.Certificate(json.loads(firebase_service_account_key_str))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        st.session_state.firebase_initialized = True
    except Exception as e:
        st.error(f"Error initializing Firebase: {e}")
        st.session_state.firebase_initialized = False
else:
    db = firestore.client()
    st.session_state.firebase_initialized = True

# --- OpenAI API Key Setup ---
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.openai_initialized = True
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets. Please add it.")
    st.session_state.openai_initialized = False

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- Helper Functions ---

def hash_password(password):
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    """Checks if a password matches a hashed password."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_user_doc_ref(username):
    """Returns the Firestore document reference for a given username."""
    # Using a simple collection for users for this example.
    # In a real app, you might structure this under a specific app ID.
    return db.collection('users').document(username)

def load_user_data(username):
    """Loads user data from Firestore."""
    doc_ref = get_user_doc_ref(username)
    user_doc = doc_ref.get()
    if user_doc.exists:
        st.session_state.user_data = user_doc.to_dict()
        st.session_state.chat_history = st.session_state.user_data.get('chat_history', [])
        return True
    return False

def update_user_data(data):
    """Updates user data in Firestore."""
    if st.session_state.username:
        doc_ref = get_user_doc_ref(st.session_state.username)
        doc_ref.set(data, merge=True) # Use merge=True to update specific fields
        st.session_state.user_data = data # Update session state immediately
        return True
    return False

def save_chat_history():
    """Saves the current chat history to Firestore."""
    if st.session_state.username and st.session_state.user_data:
        doc_ref = get_user_doc_ref(st.session_state.username)
        doc_ref.update({'chat_history': st.session_state.chat_history})

# --- Pages ---

def login_page():
    """Displays the login page."""
    st.title("AI Tutor Platform - Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if not st.session_state.firebase_initialized:
                st.error("Firebase is not initialized. Cannot log in.")
                return

            user_doc_ref = get_user_doc_ref(username)
            user_doc = user_doc_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                if check_password(password, user_data['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_data = user_data
                    st.session_state.chat_history = user_data.get('chat_history', [])
                    st.session_state.current_page = 'tutor' # Redirect to tutor page after login
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("Username not found.")

    st.markdown("---")
    st.write("Don't have an account?")
    if st.button("Register Here"):
        st.session_state.current_page = 'register'
        st.rerun()

    st.write("Forgot your password?")
    if st.button("Reset Password"):
        # This would typically link to an external password reset service
        st.info("Password reset functionality is not implemented in this demo. Please contact support.")

def register_page():
    """Displays the user registration page."""
    st.title("AI Tutor Platform - Register")

    with st.form("register_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        # Placeholder for reCAPTCHA
        st.info("reCAPTCHA integration is typically handled server-side for security. This is a placeholder.")
        # reCAPTCHA_response = st.text_input("Enter reCAPTCHA response (placeholder)") # Simulate reCAPTCHA input

        submit_button = st.form_submit_button("Register")

        if submit_button:
            if not st.session_state.firebase_initialized:
                st.error("Firebase is not initialized. Cannot register.")
                return

            if password != confirm_password:
                st.error("Passwords do not match.")
            elif not username or not password or not first_name or not last_name or not email:
                st.error("All fields are required.")
            else:
                user_doc_ref = get_user_doc_ref(username)
                if user_doc_ref.get().exists:
                    st.error("Username already exists. Please choose a different one.")
                else:
                    hashed_pass = hash_password(password)
                    initial_tokens = 1000
                    user_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'username': username,
                        'password_hash': hashed_pass,
                        'tokens': initial_tokens,
                        'learning_preferences': {
                            'style': 'interactive',
                            'pace': 'moderate',
                            'difficulty': 'beginner'
                        },
                        'subjects': [],
                        'chat_history': []
                    }
                    user_doc_ref.set(user_data)
                    st.success("Registration successful! You can now log in.")
                    st.session_state.current_page = 'login'
                    st.rerun()

    st.markdown("---")
    st.write("Already have an account?")
    if st.button("Login Here"):
        st.session_state.current_page = 'login'
        st.rerun()

def profile_page():
    """Displays the user profile page."""
    st.title("User Profile")

    if not st.session_state.logged_in or not st.session_state.user_data:
        st.warning("Please log in to view your profile.")
        st.session_state.current_page = 'login'
        st.rerun()
        return

    user_data = st.session_state.user_data

    st.header("Personal Information")
    st.write(f"**Username:** {user_data.get('username', 'N/A')}")
    st.write(f"**First Name:** {user_data.get('first_name', 'N/A')}")
    st.write(f"**Last Name:** {user_data.get('last_name', 'N/A')}")
    st.write(f"**Email:** {user_data.get('email', 'N/A')}")
    st.write(f"**Tokens Remaining:** {user_data.get('tokens', 'N/A')}")

    st.header("Password Reset")
    st.info("To reset your password, please contact support or use the 'Forgot Password' link on the login page (if implemented externally).")

    st.header("Learning Preferences")
    current_preferences = user_data.get('learning_preferences', {})
    with st.form("learning_preferences_form"):
        st.subheader("Update Your Learning Preferences")
        learning_style = st.selectbox(
            "Preferred Learning Style:",
            ['Interactive', 'Visual', 'Auditory', 'Reading/Writing', 'Kinesthetic'],
            index=['Interactive', 'Visual', 'Auditory', 'Reading/Writing', 'Kinesthetic'].index(current_preferences.get('style', 'Interactive'))
        )
        learning_pace = st.selectbox(
            "Preferred Learning Pace:",
            ['Slow', 'Moderate', 'Fast'],
            index=['Slow', 'Moderate', 'Fast'].index(current_preferences.get('pace', 'Moderate'))
        )
        difficulty_level = st.selectbox(
            "Preferred Difficulty Level:",
            ['Beginner', 'Intermediate', 'Advanced'],
            index=['Beginner', 'Intermediate', 'Advanced'].index(current_preferences.get('difficulty', 'Beginner'))
        )
        update_pref_button = st.form_submit_button("Update Preferences")

        if update_pref_button:
            user_data['learning_preferences'] = {
                'style': learning_style,
                'pace': learning_pace,
                'difficulty': difficulty_level
            }
            if update_user_data(user_data):
                st.success("Learning preferences updated successfully!")
            else:
                st.error("Failed to update learning preferences.")

    st.header("Subjects")
    available_subjects = [
        "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
        "History", "Geography", "Literature", "Economics", "Art"
    ]
    current_subjects = user_data.get('subjects', [])

    with st.form("subjects_form"):
        st.subheader("Select Your Subjects (Max 5)")
        selected_subjects = st.multiselect(
            "Choose subjects:",
            available_subjects,
            default=current_subjects
        )
        update_subjects_button = st.form_submit_button("Update Subjects")

        if update_subjects_button:
            if len(selected_subjects) > 5:
                st.error("You can select a maximum of 5 subjects.")
            else:
                user_data['subjects'] = selected_subjects
                if update_user_data(user_data):
                    st.success("Subjects updated successfully!")
                else:
                    st.error("Failed to update subjects.")

    st.markdown("---")
    if st.button("Go to Tutor Page"):
        st.session_state.current_page = 'tutor'
        st.rerun()

def tutor_page():
    """Displays the AI tutor chat page."""
    st.title("AI Tutor Chat")

    if not st.session_state.logged_in or not st.session_state.user_data:
        st.warning("Please log in to access the tutor.")
        st.session_state.current_page = 'login'
        st.rerun()
        return

    if not st.session_state.openai_initialized:
        st.error("OpenAI API is not initialized. Cannot use tutor.")
        return

    user_data = st.session_state.user_data
    current_tokens = user_data.get('tokens', 0)
    st.sidebar.metric("Tokens Remaining", current_tokens)

    st.sidebar.header("Your Settings")
    st.sidebar.write(f"**Username:** {user_data.get('username', 'N/A')}")
    st.sidebar.write(f"**Learning Style:** {user_data.get('learning_preferences', {}).get('style', 'N/A')}")
    st.sidebar.write(f"**Subjects:** {', '.join(user_data.get('subjects', ['N/A']))}")

    # Dummy syllabus and grade for context
    sample_syllabi = {
        "Mathematics": "Topics include Algebra, Geometry, Calculus basics, and Statistics.",
        "Physics": "Covers Mechanics, Thermodynamics, Electromagnetism, and Optics.",
        "Computer Science": "Includes Programming fundamentals, Data Structures, Algorithms, and Web Development basics."
    }
    student_grade = st.sidebar.selectbox("Your Grade Level:", ["Elementary", "Middle School", "High School", "College"], index=2) # Default to High School

    # --- Chat Interface ---
    col1, col2 = st.columns([1, 2]) # Input on left, output/history on right

    with col1:
        st.subheader("Your Input")
        user_input = st.text_area("Type your question here:", height=150, key="user_input_area")
        send_button = st.button("Send to Tutor")

    with col2:
        st.subheader("Chat History")
        chat_display_area = st.container(height=400, border=True)

        for chat_message in st.session_state.chat_history:
            if chat_message["role"] == "user":
                chat_display_area.markdown(f"**You:** {chat_message['content']}")
            else:
                chat_display_area.markdown(f"**Tutor:** {chat_message['content']}")
        
        # Scroll to bottom
        st.markdown("<script>window.scrollTo(0, document.body.scrollHeight);</script>", unsafe_allow_html=True)

    if send_button and user_input:
        if current_tokens <= 0:
            st.error("You have no tokens left! Please contact support for more.")
            return

        # Decrement tokens
        user_data['tokens'] -= 1
        update_user_data(user_data) # Save updated tokens to Firestore

        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        save_chat_history() # Save history to Firestore

        # Construct AI prompt context
        preferences_str = ", ".join([f"{k}: {v}" for k, v in user_data.get('learning_preferences', {}).items()])
        subjects_str = ", ".join(user_data.get('subjects', []))
        syllabus_info = ""
        for subject in user_data.get('subjects', []):
            if subject in sample_syllabi:
                syllabus_info += f"For {subject}, the syllabus covers: {sample_syllabi[subject]}. "

        system_prompt = f"""
        You are an AI tutor. Your responses should be tailored to the student's preferences and selected subjects.
        Student's Grade Level: {student_grade}
        Student's Learning Preferences: {preferences_str}
        Student's Selected Subjects: {subjects_str}
        Subject Syllabus Information: {syllabus_info}
        Be helpful, patient, and provide clear explanations.
        """

        messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history

        try:
            # Call OpenAI API
            with st.spinner("Tutor is thinking..."):
                client = openai.OpenAI(api_key=openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo", # Or "gpt-4" if you have access
                    messages=messages,
                    max_tokens=200,
                    temperature=0.7,
                )
                tutor_response = response.choices[0].message.content
            
            # Add tutor response to history
            st.session_state.chat_history.append({"role": "assistant", "content": tutor_response})
            save_chat_history() # Save updated history to Firestore
            st.rerun() # Rerun to update chat display and token count

        except openai.APIError as e:
            st.error(f"OpenAI API error: {e}")
            # Revert token decrement if API call fails
            user_data['tokens'] += 1
            update_user_data(user_data)
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            # Revert token decrement if API call fails
            user_data['tokens'] += 1
            update_user_data(user_data)

    st.markdown("---")
    if st.button("Back to Profile"):
        st.session_state.current_page = 'profile'
        st.rerun()

# --- Main App Logic ---
def main():
    """Controls the flow of the Streamlit application."""
    st.sidebar.title("Navigation")
    if st.session_state.logged_in:
        if st.sidebar.button("Profile"):
            st.session_state.current_page = 'profile'
            st.rerun()
        if st.sidebar.button("Tutor"):
            st.session_state.current_page = 'tutor'
            st.rerun()
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_data = None
            st.session_state.chat_history = []
            st.session_state.current_page = 'login'
            st.rerun()
    else:
        if st.sidebar.button("Login"):
            st.session_state.current_page = 'login'
            st.rerun()
        if st.sidebar.button("Register"):
            st.session_state.current_page = 'register'
            st.rerun()

    if st.session_state.current_page == 'login':
        login_page()
    elif st.session_state.current_page == 'register':
        register_page()
    elif st.session_state.current_page == 'profile':
        profile_page()
    elif st.session_state.current_page == 'tutor':
        tutor_page()

if __name__ == "__main__":
    main()
