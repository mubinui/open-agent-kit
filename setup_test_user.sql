-- Insert test user (password: admin123)
INSERT INTO users (id, username, email, password_hash, role, active, created_at)
VALUES (
    gen_random_uuid(),
    'admin',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYILSBiOzNu',
    'ADMIN',
    TRUE,
    NOW()
)
ON CONFLICT (username) DO NOTHING;

SELECT 'Test user created: username=admin, password=admin123' as message;
