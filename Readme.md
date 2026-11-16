# 📋 Handover & Attendance Web Application

A full-featured, mobile-friendly multi-user **Handover Application** built using Python, Streamlit, and MySQL.

## 🚀 Key Features
1. **Role-Based Authentication**: Super Admin and regular User roles.
2. **Attendance Tracking & Shift Timers**: 
   - Support for Day, Night, and General shifts.
   - Real-time ticking shift countdown timers upon check-in.
   - Automatic late-arrival calculation (`HH:MM:SS`).
   - One-click structured Excel report export.
   - Single-punch restriction per calendar day.
3. **Tree-Structured Follow-up Tasks**: Segregate handovers by date with nested parent-child task threads and status management.
4. **Incident Logging**: Track technical node issues with custom node names and descriptions.
5. **Mobile-Friendly UI**: Optimized viewports and responsive touch targets for smartphones.

---

## 🛠️ Installation & Setup

### 1. Database Setup
Run the script provided in `database_setup.sql` on your MySQL server to set up the database and default admin credentials:
- **Username:** `admin`
- **Password:** `password123`

### 2. Install Dependencies
Open your terminal inside the project directory and install the requirements:
```bash
pip install -r requirements.txt