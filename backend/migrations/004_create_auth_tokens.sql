CREATE TABLE IF NOT EXISTS auth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token_type VARCHAR(50),
    encrypted_token TEXT,
    expires_at TIMESTAMP,
    health_status VARCHAR(50) DEFAULT 'HEALTHY',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_auth_tokens_id ON auth_tokens (id);
CREATE INDEX IF NOT EXISTS ix_auth_tokens_user_id ON auth_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_auth_tokens_token_type ON auth_tokens (token_type);
