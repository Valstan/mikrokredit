-- Initialize mikrokredit database
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE mikrokredit_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mikrokredit_db')\gexec

-- Connect to the mikrokredit_db database
\c mikrokredit_db;

-- Create sequences for auto-incrementing IDs
CREATE SEQUENCE IF NOT EXISTS loans_id_seq;
CREATE SEQUENCE IF NOT EXISTS installments_id_seq;

-- Create loans table
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY DEFAULT nextval('loans_id_seq'),
    website VARCHAR NOT NULL,
    loan_date VARCHAR NOT NULL,
    amount_borrowed FLOAT NOT NULL,
    amount_due FLOAT NOT NULL,
    due_date VARCHAR NOT NULL,
    risky_org INTEGER DEFAULT 0 NOT NULL,
    notes TEXT,
    payment_methods TEXT,
    reminded_pre_due INTEGER DEFAULT 0 NOT NULL,
    created_at VARCHAR NOT NULL,
    is_paid INTEGER DEFAULT 0 NOT NULL,
    org_name TEXT
);

-- Create installments table
CREATE TABLE IF NOT EXISTS installments (
    id INTEGER PRIMARY KEY DEFAULT nextval('installments_id_seq'),
    loan_id INTEGER NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    due_date VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    paid INTEGER DEFAULT 0 NOT NULL,
    paid_date VARCHAR,
    created_at VARCHAR NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_loans_due_date ON loans(due_date);
CREATE INDEX IF NOT EXISTS idx_installments_loan_id ON installments(loan_id);
CREATE INDEX IF NOT EXISTS idx_installments_due_date ON installments(due_date);
CREATE INDEX IF NOT EXISTS idx_installments_paid ON installments(paid);

-- Grant permissions to the user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mikrokredit_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mikrokredit_user;
