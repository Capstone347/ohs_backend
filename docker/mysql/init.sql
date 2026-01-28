-- ===========================================
-- OHS Remote Development Database Setup
-- ===========================================
-- This script automatically runs when the MySQL
-- container is first created (development only)
-- ===========================================

-- Ensure database exists
CREATE DATABASE IF NOT EXISTS ohs_remote_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant permissions to dev user
GRANT ALL PRIVILEGES ON ohs_remote_dev.* TO 'ohs_dev_user'@'%';
FLUSH PRIVILEGES;

-- Use the database
USE ohs_remote_dev;

-- Log initialization
SELECT 'Database ohs_remote_dev initialized successfully' AS message;
