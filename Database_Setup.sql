CREATE DATABASE IF NOT EXISTS handover_db;
USE handover_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'User',
    shift VARCHAR(20) NOT NULL DEFAULT 'General'
);

-- Insert Default Super Admin (Username: admin, Password: password123)
INSERT INTO users (username, password, role, shift) 
VALUES ('admin', 'password123', 'Super Admin', 'General')
ON DUPLICATE KEY UPDATE username=username;

-- 2. Attendance Table
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    punch_type VARCHAR(20) NOT NULL,
    timestamp DATETIME NOT NULL,
    shift VARCHAR(20) NOT NULL,
    late_duration VARCHAR(50) DEFAULT '00:00:00'
);

-- 3. Tasks / Followup Table (Supports hierarchical tree structure)
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    task_description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    created_at DATETIME NOT NULL,
    parent_id INT DEFAULT NULL
);

-- 4. Incidents Table
CREATE TABLE IF NOT EXISTS incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    nodename VARCHAR(100) NOT NULL,
    issue TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Open',
    created_at DATETIME NOT NULL
);