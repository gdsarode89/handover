from datetime import datetime, timedelta, date
import io
import mysql.connector
import pandas as pd
import streamlit as st

# --- DATABASE CONNECTION ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # Change to your MySQL username
        password="",          # Change to your MySQL password
        database="handover_db"
    )

st.set_page_config(
    page_title="Handover App", 
    page_icon="📋", 
    layout="wide",
    initial_sidebar_state="auto"
)

# --- MOBILE-FRIENDLY CSS INJECTION ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }
    [data-testid="stDataFrame"] {
        width: 100%;
        overflow-x: auto;
    }
    input, textarea, select {
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.shift = ""

# --- HELPER FUNCTION FOR LATE CALCULATION ---
def calculate_late_time(punch_time, shift_name, shift_hours):
    start_hour = shift_hours[shift_name]["start"]
    scheduled_start = punch_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    if shift_name == "Night" and punch_time.hour < 8:
        scheduled_start -= timedelta(days=1)

    if punch_time > scheduled_start:
        late_delta = punch_time - scheduled_start
        total_seconds = int(late_delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return True, f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return False, "00:00:00"

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    st.title("🔐 Handover App - Login")
    
    tab_login, tab_info = st.tabs(["Login", "Default Info"])
    
    with tab_login:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.session_state.shift = user["shift"]
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            except Exception as e:
                st.error(f"Database connection error: {e}")
                
    with tab_info:
        st.info("Default Super Admin Credentials:\n- **Username:** admin\n- **Password:** password123\n\nAsk your Super Admin to create new user accounts.")
        
    st.stop()

# --- MAIN APP INTERFACE ---
st.sidebar.title(f"Welcome, {st.session_state.username}")
st.sidebar.markdown(f"**Role:** {st.session_state.role}")
st.sidebar.markdown(f"**Default Shift:** {st.session_state.shift}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.shift = ""
    st.rerun()

# Navigation Tabs
tabs = ["Attendance", "Followup Tasks", "Create Incident"]
if st.session_state.role == "Super Admin":
    tabs.append("Super Admin Panel")

selected_tab = st.sidebar.radio("Navigation", tabs)

# --- TAB 1: ATTENDANCE ---
if selected_tab == "Attendance":
    st.header("🕒 Attendance & Shift Management")
    
    shift_hours = {
        "Day": {"start": 8, "end": 20, "duration": 12},     # 08:00 to 20:00
        "Night": {"start": 20, "end": 8, "duration": 12},    # 20:00 to 08:00
        "General": {"start": 10, "end": 18, "duration": 8}   # 10:00 to 18:00
    }
    
    shift_options = ["Day", "Night", "General"]
    default_index = shift_options.index(st.session_state.shift) if st.session_state.shift in shift_options else 2
    
    selected_shift = st.selectbox("Select Your Shift for Punching", shift_options, index=default_index)
    
    current_shift_info = shift_hours.get(selected_shift, shift_hours['General'])
    st.info(f"Selected Shift: **{selected_shift}** ({current_shift_info['start']:02d}:00 - {current_shift_info['end']:02d}:00)")
    
    today_date = datetime.now().date()
    try:
        conn = get_db_connection()
        query = "SELECT punch_type, timestamp FROM attendance WHERE username = %s AND DATE(timestamp) = %s ORDER BY id DESC LIMIT 1"
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (st.session_state.username, today_date))
        last_today = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        last_today = None

    already_punched_in_today = last_today and last_today["punch_type"] == "Punch In"
    already_punched_out_today = last_today and last_today["punch_type"] == "Punch Out"

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Punch Action")
        
        if already_punched_in_today:
            st.info("🔒 Already **Punched In** today.")
        elif already_punched_out_today:
            st.info("🔒 Attendance cycle completed for today.")
        else:
            if st.button("Punch In", type="primary"):
                try:
                    now = datetime.now()
                    is_late, late_str = calculate_late_time(now, selected_shift, shift_hours)
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO attendance (username, punch_type, timestamp, shift, late_duration) VALUES (%s, %s, %s, %s, %s)",
                        (st.session_state.username, "Punch In", now, selected_shift, late_str)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"✅ Punched In at {now.strftime('%H:%M:%S')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                
        if already_punched_in_today:
            if st.button("Punch Out"):
                try:
                    now = datetime.now()
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO attendance (username, punch_type, timestamp, shift, late_duration) VALUES (%s, %s, %s, %s, %s)",
                        (st.session_state.username, "Punch Out", now, selected_shift, "00:00:00")
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"Punched Out at {now.strftime('%H:%M:%S')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        st.subheader("Shift Timer")
        
        @st.fragment(run_every=1)
        def render_live_timer():
            try:
                conn = get_db_connection()
                query = "SELECT punch_type, timestamp, shift, late_duration FROM attendance WHERE username = %s ORDER BY id DESC LIMIT 1"
                df_last = pd.read_sql(query, conn, params=(st.session_state.username,))
                conn.close()
                
                if not df_last.empty and df_last.iloc[0]["punch_type"] == "Punch In":
                    punch_time = pd.to_datetime(df_last.iloc[0]["timestamp"])
                    punched_shift = df_last.iloc[0]["shift"]
                    late_dur = df_last.iloc[0]["late_duration"]
                    
                    duration_hours = shift_hours.get(punched_shift, shift_hours["General"])["duration"]
                    shift_end_time = punch_time + timedelta(hours=duration_hours)
                    
                    st.success(f"Status: **Punched In** ({punched_shift})")
                    if late_dur and late_dur != "00:00:00":
                        st.error(f"🚨 Late: **{late_dur}**")
                        
                    st.write(f"**In:** {punch_time.strftime('%H:%M:%S')}")
                    st.write(f"**Ends:** {shift_end_time.strftime('%H:%M:%S')}")
                    
                    remaining_time = shift_end_time - datetime.now()
                    if remaining_time.total_seconds() > 0:
                        hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        st.metric(label="⏳ Remaining", value=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                    else:
                        st.warning("Shift finished!")
                else:
                    st.info("Status: **Punched Out**")
            except Exception as e:
                st.warning("Timer unavailable.")
                
        render_live_timer()

    st.markdown("---")
    st.subheader("Attendance Logs & Export")
    
    try:
        conn = get_db_connection()
        if st.session_state.role == "Super Admin":
            raw_df = pd.read_sql("SELECT id, username, punch_type, timestamp, shift, late_duration FROM attendance ORDER BY id ASC", conn)
        else:
            raw_df = pd.read_sql("SELECT id, username, punch_type, timestamp, shift, late_duration FROM attendance WHERE username = %s ORDER BY id ASC", conn, params=(st.session_state.username,))
        conn.close()

        paired_records = []
        active_punches = {}

        for _, row in raw_df.iterrows():
            user = row["username"]
            if row["punch_type"] == "Punch In":
                if user in active_punches:
                    prev = active_punches[user]
                    paired_records.append({
                        "Username": user,
                        "Shift": prev["shift"],
                        "Punch In": prev["timestamp"],
                        "Punch Out": "Not Out",
                        "Late By": prev["late_duration"],
                        "Status": "Late" if prev["late_duration"] != "00:00:00" else "On Time"
                    })
                active_punches[user] = row
            elif row["punch_type"] == "Punch Out":
                if user in active_punches:
                    prev = active_punches.pop(user)
                    paired_records.append({
                        "Username": user,
                        "Shift": prev["shift"],
                        "Punch In": prev["timestamp"],
                        "Punch Out": row["timestamp"],
                        "Late By": prev["late_duration"],
                        "Status": "Late" if prev["late_duration"] != "00:00:00" else "On Time"
                    })

        for user, prev in active_punches.items():
            paired_records.append({
                "Username": user,
                "Shift": prev["shift"],
                "Punch In": prev["timestamp"],
                "Punch Out": "Active",
                "Late By": prev["late_duration"],
                "Status": "Late" if prev["late_duration"] != "00:00:00" else "On Time"
            })

        export_df = pd.DataFrame(paired_records)
        if not export_df.empty:
            export_df = export_df.iloc[::-1]

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Attendance_Report')
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Export Attendance to Excel",
                data=excel_data,
                file_name=f"Attendance_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.dataframe(export_df, use_container_width=True)
        else:
            st.info("No records found.")

    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 2: FOLLOWUP TASKS (ASCII TREE & UPDATES) ---
elif selected_tab == "Followup Tasks":
    st.header("📝 Task Followups & Handover Tree")
    
    selected_date = st.date_input("Filter Tasks by Date", value=date.today())
    
    with st.form("new_root_task", clear_on_submit=True):
        root_desc = st.text_area("Create New Main Task / Handover")
        root_submitted = st.form_submit_button("Post Main Task")
        if root_submitted and root_desc.strip():
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (username, task_description, status, created_at, parent_id) VALUES (%s, %s, %s, %s, NULL)",
                    (st.session_state.username, root_desc, "Pending", datetime.now())
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.success("Main task posted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader(f"Task Tree for {selected_date}")
    
    try:
        conn = get_db_connection()
        tasks_df = pd.read_sql("SELECT id, username, task_description, status, created_at, parent_id FROM tasks ORDER BY id ASC", conn)
        conn.close()
        
        if tasks_df.empty:
            st.info("No tasks recorded yet.")
        else:
            tasks_df["task_date"] = pd.to_datetime(tasks_df["created_at"]).dt.date
            root_tasks = tasks_df[tasks_df["parent_id"].isna()]
            
            def matches_date_recursive(task_id, target_date):
                row = tasks_df[tasks_df["id"] == task_id]
                if row.empty:
                    return False
                if row.iloc[0]["task_date"] == target_date:
                    return True
                children = tasks_df[tasks_df["parent_id"] == task_id]
                for _, child in children.iterrows():
                    if matches_date_recursive(child["id"], target_date):
                        return True
                return False

            filtered_roots = root_tasks[root_tasks["id"].apply(lambda tid: matches_date_recursive(tid, selected_date))]

            if filtered_roots.empty:
                st.info(f"No task threads found for {selected_date}.")
            else:
                def generate_ascii_tree(parent_id, prefix=""):
                    subset = tasks_df[tasks_df["parent_id"] == parent_id]
                    lines = []
                    subset_list = list(subset.iterrows())
                    for i, (_, row) in enumerate(subset_list):
                        is_last = (i == len(subset_list) - 1)
                        connector = "└── " if is_last else "├── "
                        dt_str = pd.to_datetime(row['created_at']).strftime('%Y-%m-%d %H:%M')
                        line_str = f"{prefix}{connector}{row['task_description']}  (👤 {row['username']} | 📅 {dt_str} | Status: {row['status']})"
                        lines.append(line_str)
                        extension = "    " if is_last else "│   "
                        lines.extend(generate_ascii_tree(row['id'], prefix + extension))
                    return lines

                full_tree_text = "│\n"
                for _, root_row in filtered_roots.iterrows():
                    root_dt = pd.to_datetime(root_row['created_at']).strftime('%Y-%m-%d %H:%M')
                    full_tree_text += f"├── {root_row['task_description']}  (👤 {root_row['username']} | 📅 {root_dt} | Status: {root_row['status']})\n"
                    sub_lines = generate_ascii_tree(root_row['id'], prefix="│   ")
                    for line in sub_lines:
                        full_tree_text += f"{line}\n"
                
                st.code(full_tree_text, language="text")

                st.markdown("### Manage & Add Updates / Subtasks")
                for _, root_row in filtered_roots.iterrows():
                    root_id = root_row["id"]
                    with st.expander(f"Manage Task: {root_row['task_description']} (ID: {root_id})"):
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            new_status = st.selectbox(
                                "Update Main Status", 
                                ["Pending", "Completed"], 
                                index=0 if root_row['status'] == "Pending" else 1,
                                key=f"status_select_{root_id}"
                            )
                            if new_status != root_row['status']:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, root_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                                st.success("Status updated!")
                                st.rerun()
                                
                        with col_m2:
                            with st.form(key=f"add_sub_{root_id}"):
                                sub_desc = st.text_input("Add Subtask / Update")
                                sub_submit = st.form_submit_button("Post Update")
                                if sub_submit and sub_desc.strip():
                                    conn = get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "INSERT INTO tasks (username, task_description, status, created_at, parent_id) VALUES (%s, %s, %s, %s, %s)",
                                        (st.session_state.username, sub_desc, "Pending", datetime.now(), root_id)
                                    )
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                    st.success("Update/Subtask posted!")
                                    st.rerun()
            
    except Exception as e:
        st.error(f"Error loading tasks: {e}")

# --- TAB 3: CREATE INCIDENT ---
elif selected_tab == "Create Incident":
    st.header("🚨 Create Incident")
    
    with st.form("incident_form", clear_on_submit=True):
        nodename = st.text_input("Node Name")
        issue = st.text_area("Issue Description")
        submit_incident = st.form_submit_button("Submit Incident", type="primary")
        
        if submit_incident:
            if nodename.strip() and issue.strip():
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO incidents (username, nodename, issue, status, created_at) VALUES (%s, %s, %s, %s, %s)",
                        (st.session_state.username, nodename, issue, "Open", datetime.now())
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success("Incident created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating incident: {e}")
            else:
                st.warning("Please fill in both Node Name and Issue description.")

    st.markdown("---")
    st.subheader("All Incidents Log")
    
    try:
        conn = get_db_connection()
        incidents_df = pd.read_sql("SELECT username, nodename, issue, created_at FROM incidents ORDER BY id DESC", conn)
        conn.close()
        
        if incidents_df.empty:
            st.info("No incidents logged yet.")
        else:
            incidents_df.columns = ["Username", "Node Name", "Issue Description", "Created At"]
            st.dataframe(incidents_df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading incidents: {e}")

# --- TAB 4: SUPER ADMIN PANEL ---
elif selected_tab == "Super Admin Panel":
    if st.session_state.role != "Super Admin":
        st.error("⛔ Access Denied. Only Super Admins can access this panel.")
        st.stop()
        
    st.header("👑 Super Admin User Management")
    
    st.subheader("Create New User")
    with st.form("create_user_form", clear_on_submit=True):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        new_role = st.selectbox("Role", ["User", "Super Admin"])
        
        create_submitted = st.form_submit_button("Create User")
        if create_submitted and new_username and new_password:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password, role, shift) VALUES (%s, %s, %s, 'General')",
                    (new_username, new_password, new_role)
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.success(f"User '{new_username}' created successfully!")
            except mysql.connector.Error as err:
                st.error(f"Error: {err}")
                
    st.markdown("---")
    st.subheader("Existing Users List")
    try:
        conn = get_db_connection()
        users_df = pd.read_sql("SELECT id, username, role, shift FROM users", conn)
        conn.close()
        st.dataframe(users_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading users: {e}")