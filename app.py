import json
import os
import streamlit as st
from datetime import datetime
import pandas as pd
import hashlib

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="USMLE Question Bank",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ---------------- USER AUTHENTICATION ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

def create_user(username, password):
    users = load_users()
    if username in users:
        return False, "Username already exists"
    users[username] = {
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "progress": {
            "questions_attempted": [],
            "correct_questions": [],
            "incorrect_questions": [],
            "marked_questions": [],
            "performance_by_system": {},
            "performance_by_subject": {}
        }
    }
    save_users(users)
    return True, "User created successfully"

def authenticate_user(username, password):
    users = load_users()
    if username not in users:
        return False, "User not found"
    if users[username]["password_hash"] == hash_password(password):
        return True, "Login successful"
    return False, "Invalid password"

def save_user_progress(username):
    users = load_users()
    if username in users:
        progress = st.session_state.user_progress
        users[username]["progress"] = {
            "questions_attempted": list(progress["questions_attempted"]),
            "correct_questions": list(progress["correct_questions"]),
            "incorrect_questions": list(progress["incorrect_questions"]),
            "marked_questions": list(progress["marked_questions"]),
            "performance_by_system": progress["performance_by_system"],
            "performance_by_subject": progress["performance_by_subject"],
            "last_saved": datetime.now().isoformat()
        }
        save_users(users)

def load_user_progress(username):
    users = load_users()
    if username in users:
        progress = users[username]["progress"]
        return {
            "questions_attempted": set(progress.get("questions_attempted", [])),
            "correct_questions": set(progress.get("correct_questions", [])),
            "incorrect_questions": set(progress.get("incorrect_questions", [])),
            "marked_questions": set(progress.get("marked_questions", [])),
            "performance_by_system": progress.get("performance_by_system", {}),
            "performance_by_subject": progress.get("performance_by_subject", {})
        }
    return {
        "questions_attempted": set(),
        "correct_questions": set(),
        "incorrect_questions": set(),
        "marked_questions": set(),
        "performance_by_system": {},
        "performance_by_subject": {}
    }

# ---------------- LOAD QUESTIONS ----------------
@st.cache_data
def load_questions():
    json_path = "questions.json"
    if not os.path.exists(json_path):
        st.error("❌ questions.json not found")
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    
    return questions

questions = load_questions()

# ---------------- SESSION STATE ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_progress = {
        "questions_attempted": set(),
        "correct_questions": set(),
        "incorrect_questions": set(),
        "marked_questions": set(),
        "performance_by_system": {},
        "performance_by_subject": {}
    }

if "quiz_config" not in st.session_state:
    st.session_state.quiz_config = {
        "num_questions": 10,
        "selected_systems": [],
        "selected_subjects": [],
        "question_filter": "unused",
        "current_quiz": [],
        "quiz_started": False
    }

if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = {
        "idx": 0,
        "score": 0,
        "answered": False,
        "selected": None,
        "marked": set(),
        "quiz_start_time": None
    }

# ---------------- HOME PAGE ----------------
def show_home():
    st.title("🏠 USMLE Question Bank")
    
    if not st.session_state.logged_in:
        st.warning("Please login or create an account to start")
        return
    
    st.write(f"Welcome back, **{st.session_state.username}**!")
    
    # Quick Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Questions", len(questions))
    with col2:
        attempted = len(st.session_state.user_progress["questions_attempted"])
        st.metric("Attempted", attempted)
    with col3:
        correct = len(st.session_state.user_progress["correct_questions"])
        accuracy = (correct/attempted*100) if attempted > 0 else 0
        st.metric("Accuracy", f"{accuracy:.1f}%")
    with col4:
        st.metric("Marked", len(st.session_state.user_progress["marked_questions"]))
    
    st.divider()
    
    # Quiz Configuration
    st.subheader("📝 Configure Your Quiz")
    
    # Number of questions
    max_q = min(100, len(questions))
    num_q = st.slider("Number of questions", 5, max_q, 20, 5)
    
    # Filter by system
    all_systems = sorted(set([q.get("system", "General") for q in questions]))
    selected_systems = st.multiselect(
        "Select systems (leave empty for all):",
        all_systems,
        placeholder="All systems"
    )
    
    # Filter by subject
    all_subjects = sorted(set([q.get("subject", "General") for q in questions]))
    selected_subjects = st.multiselect(
        "Select subjects (leave empty for all):",
        all_subjects,
        placeholder="All subjects"
    )
    
    # Question filter
    filter_option = st.radio(
        "Question selection:",
        ["Unused questions", "Marked questions", "Incorrect questions", "All questions"],
        horizontal=True
    )
    
    # Map filter to values
    filter_map = {
        "Unused questions": "unused",
        "Marked questions": "marked",
        "Incorrect questions": "incorrect",
        "All questions": "all"
    }
    
    # Start Quiz Button
    if st.button("🚀 Start Quiz", type="primary", use_container_width=True):
        # Filter questions based on selection
        filtered_questions = questions.copy()
        
        # Filter by system
        if selected_systems:
            filtered_questions = [q for q in filtered_questions if q.get("system", "General") in selected_systems]
        
        # Filter by subject
        if selected_subjects:
            filtered_questions = [q for q in filtered_questions if q.get("subject", "General") in selected_subjects]
        
        # Apply question filter
        if filter_map[filter_option] == "marked":
            marked_ids = st.session_state.user_progress["marked_questions"]
            filtered_questions = [q for q in filtered_questions if q["id"] in marked_ids]
        elif filter_map[filter_option] == "incorrect":
            incorrect_ids = st.session_state.user_progress["incorrect_questions"]
            filtered_questions = [q for q in filtered_questions if q["id"] in incorrect_ids]
        elif filter_map[filter_option] == "unused":
            attempted_ids = st.session_state.user_progress["questions_attempted"]
            filtered_questions = [q for q in filtered_questions if q["id"] not in attempted_ids]
        
        # Limit number of questions
        import random
        if len(filtered_questions) > num_q:
            filtered_questions = random.sample(filtered_questions, num_q)
        
        if not filtered_questions:
            st.error("No questions match your criteria. Try different filters.")
            return
        
        # Save quiz configuration
        st.session_state.quiz_config = {
            "num_questions": num_q,
            "selected_systems": selected_systems,
            "selected_subjects": selected_subjects,
            "question_filter": filter_map[filter_option],
            "current_quiz": filtered_questions,
            "quiz_started": True
        }
        
        # Reset quiz state
        st.session_state.quiz_state = {
            "idx": 0,
            "score": 0,
            "answered": False,
            "selected": None,
            "marked": set(),
            "quiz_start_time": datetime.now()
        }
        
        st.rerun()

# ---------------- QUIZ PAGE ----------------
def show_quiz():
    if not st.session_state.quiz_config["quiz_started"]:
        st.warning("No active quiz. Please configure one from the home page.")
        if st.button("Go to Home"):
            st.session_state.quiz_config["quiz_started"] = False
            st.rerun()
        return
    
    quiz_questions = st.session_state.quiz_config["current_quiz"]
    quiz_state = st.session_state.quiz_state
    
    if quiz_state["idx"] >= len(quiz_questions):
        show_results(quiz_questions)
        return
    
    # Current question
    q = quiz_questions[quiz_state["idx"]]
    q_id = q["id"]
    
    # Header with navigation
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        if st.button("🏠 Home"):
            save_user_progress(st.session_state.username)
            st.session_state.quiz_config["quiz_started"] = False
            st.rerun()
    with col2:
        st.markdown(f"### Question {quiz_state['idx'] + 1} of {len(quiz_questions)}")
    with col3:
        # Mark for review button
        mark_label = "✅ Unmark" if q_id in quiz_state["marked"] else "📌 Mark for Review"
        if st.button(mark_label):
            if q_id in quiz_state["marked"]:
                quiz_state["marked"].remove(q_id)
            else:
                quiz_state["marked"].add(q_id)
            st.rerun()
    
    st.progress((quiz_state["idx"]) / len(quiz_questions))
    
    # Question info
    st.markdown(f"**{q.get('system', 'General')}** » **{q.get('subject', 'General')}** » {q.get('topic', 'General')}")
    if "difficulty" in q:
        st.caption(f"Difficulty: {q['difficulty']}")
    
    st.markdown(f"**{q['question']}**")
    
    # Options
    options = q.get("options", [])
    correct_answer = q.get("answer", "A")
    
    # Display options
    for i, opt in enumerate(options):
        letter = chr(65 + i)
        label = f"{letter}. {opt}"
        
        if st.button(
            label,
            key=f"opt_{i}",
            disabled=quiz_state["answered"],
            use_container_width=True
        ):
            quiz_state["selected"] = letter
            quiz_state["answered"] = True
            
            # Update user progress
            st.session_state.user_progress["questions_attempted"].add(q_id)
            
            if letter == correct_answer:
                quiz_state["score"] += 1
                st.session_state.user_progress["correct_questions"].add(q_id)
                if q_id in st.session_state.user_progress["incorrect_questions"]:
                    st.session_state.user_progress["incorrect_questions"].remove(q_id)
            else:
                st.session_state.user_progress["incorrect_questions"].add(q_id)
                if q_id in st.session_state.user_progress["correct_questions"]:
                    st.session_state.user_progress["correct_questions"].remove(q_id)
            
            # Update performance by system
            system = q.get("system", "General")
            subject = q.get("subject", "General")
            
            # Initialize if not exists
            if system not in st.session_state.user_progress["performance_by_system"]:
                st.session_state.user_progress["performance_by_system"][system] = {"correct": 0, "total": 0}
            if subject not in st.session_state.user_progress["performance_by_subject"]:
                st.session_state.user_progress["performance_by_subject"][subject] = {"correct": 0, "total": 0}
            
            # Update counts
            st.session_state.user_progress["performance_by_system"][system]["total"] += 1
            st.session_state.user_progress["performance_by_subject"][subject]["total"] += 1
            
            if letter == correct_answer:
                st.session_state.user_progress["performance_by_system"][system]["correct"] += 1
                st.session_state.user_progress["performance_by_subject"][subject]["correct"] += 1
    
    # Explanation
    if quiz_state["answered"]:
        st.divider()
        
        if quiz_state["selected"] == correct_answer:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Incorrect — Correct answer: **{correct_answer}**")
        
        st.markdown("#### Explanation")
        st.markdown(q.get("explanation", "No explanation available."))
        
        if "educational_objective" in q:
            st.markdown(f"🎯 **Key Point:** {q['educational_objective']}")
    
    # Navigation buttons at bottom
    st.divider()
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("◀◀ Previous") and quiz_state["idx"] > 0:
            quiz_state["idx"] -= 1
            quiz_state["answered"] = False
            quiz_state["selected"] = None
            st.rerun()
    
    with col3:
        if quiz_state["answered"]:
            if st.button("Next ▶▶", type="primary"):
                quiz_state["idx"] += 1
                quiz_state["answered"] = False
                quiz_state["selected"] = None
                st.rerun()
        else:
            st.button("Next ▶▶", disabled=True)
    
    with col5:
        if st.button("End Quiz 🏁"):
            save_user_progress(st.session_state.username)
            show_results(quiz_questions)
            return
    
    # Quick jump
    question_numbers = list(range(1, len(quiz_questions) + 1))
    selected_q = st.selectbox(
        "Jump to question:",
        question_numbers,
        index=quiz_state["idx"],
        key="jump_select"
    )
    if selected_q - 1 != quiz_state["idx"]:
        quiz_state["idx"] = selected_q - 1
        quiz_state["answered"] = False
        quiz_state["selected"] = None
        st.rerun()

# ---------------- RESULTS PAGE ----------------
def show_results(quiz_questions):
    quiz_state = st.session_state.quiz_state
    score = quiz_state["score"]
    total = len(quiz_questions)
    percentage = (score / total * 100) if total > 0 else 0
    
    st.title("📊 Quiz Results")
    
    # Score display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{score}/{total}")
    with col2:
        st.metric("Percentage", f"{percentage:.1f}%")
    with col3:
        if quiz_state["quiz_start_time"]:
            time_taken = datetime.now() - quiz_state["quiz_start_time"]
            st.metric("Time", f"{time_taken.seconds//60}:{time_taken.seconds%60:02d}")
    
    # Performance gauge
    if percentage >= 70:
        st.success("🎉 Excellent performance!")
    elif percentage >= 50:
        st.info("👍 Good effort!")
    else:
        st.warning("📚 More practice needed!")
    
    # Review marked questions
    marked = quiz_state["marked"]
    if marked:
        st.subheader("📌 Questions Marked for Review")
        for q_id in marked:
            question = next((q for q in quiz_questions if q["id"] == q_id), None)
            if question:
                st.write(f"**Q{quiz_questions.index(question)+1}:** {question['question'][:100]}...")
    
    # Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔁 Retry Same Questions"):
            st.session_state.quiz_state = {
                "idx": 0,
                "score": 0,
                "answered": False,
                "selected": None,
                "marked": set(),
                "quiz_start_time": datetime.now()
            }
            st.rerun()
    
    with col2:
        if st.button("🏠 Back to Home"):
            save_user_progress(st.session_state.username)
            st.session_state.quiz_config["quiz_started"] = False
            st.rerun()
    
    with col3:
        if st.button("📊 View Performance Analysis"):
            st.session_state.show_analysis = True
            st.rerun()

# ---------------- PERFORMANCE ANALYSIS ----------------
def show_performance_analysis():
    st.title("📈 Performance Analysis")
    
    if not st.session_state.logged_in:
        st.warning("Please login to see performance analysis")
        return
    
    progress = st.session_state.user_progress
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_attempted = len(progress["questions_attempted"])
        st.metric("Questions Attempted", total_attempted)
    with col2:
        correct = len(progress["correct_questions"])
        st.metric("Correct", correct)
    with col3:
        incorrect = len(progress["incorrect_questions"])
        st.metric("Incorrect", incorrect)
    with col4:
        accuracy = (correct/total_attempted*100) if total_attempted > 0 else 0
        st.metric("Accuracy", f"{accuracy:.1f}%")
    
    st.divider()
    
    # Performance by system
    st.subheader("Performance by System")
    if progress["performance_by_system"]:
        system_data = []
        for system, stats in progress["performance_by_system"].items():
            if stats["total"] > 0:
                accuracy = (stats["correct"]/stats["total"]*100)
                system_data.append({
                    "System": system,
                    "Correct": stats["correct"],
                    "Total": stats["total"],
                    "Accuracy": f"{accuracy:.1f}%"
                })
        
        if system_data:
            df = pd.DataFrame(system_data)
            st.dataframe(df, hide_index=True, use_container_width=True)
    
    # Performance by subject
    st.subheader("Performance by Subject")
    if progress["performance_by_subject"]:
        subject_data = []
        for subject, stats in progress["performance_by_subject"].items():
            if stats["total"] > 0:
                accuracy = (stats["correct"]/stats["total"]*100)
                subject_data.append({
                    "Subject": subject,
                    "Correct": stats["correct"],
                    "Total": stats["total"],
                    "Accuracy": f"{accuracy:.1f}%"
                })
        
        if subject_data:
            df = pd.DataFrame(subject_data)
            st.dataframe(df, hide_index=True, use_container_width=True)
    
    if st.button("🏠 Back to Home"):
        st.session_state.show_analysis = False
        st.rerun()

# ---------------- LOGIN/SIGNUP PAGE ----------------
def show_auth():
    st.title("🔐 USMLE Question Bank")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", type="primary"):
            if not login_user or not login_pass:
                st.error("Please enter both username and password")
            else:
                success, message = authenticate_user(login_user, login_pass)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.session_state.user_progress = load_user_progress(login_user)
                    st.success(f"Welcome back, {login_user}!")
                    st.rerun()
                else:
                    st.error(message)
    
    with tab2:
        st.sub