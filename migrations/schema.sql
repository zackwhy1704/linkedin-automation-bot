-- PostgreSQL Schema for LinkedIn Automation Bot
-- Migrates from SQLite + JSON files to PostgreSQL
-- Total: 13 tables (5 existing + 8 from JSON files)

-- ============================================================================
-- EXISTING TABLES (Migrated from SQLite)
-- ============================================================================

-- Users table (core user accounts and subscriptions)
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    subscription_active BOOLEAN DEFAULT FALSE,
    subscription_expires TIMESTAMP WITH TIME ZONE,
    stripe_customer_id VARCHAR(255) UNIQUE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    last_seen TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_subscription ON users(subscription_active, subscription_expires);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE INDEX idx_users_last_seen ON users(last_seen DESC);

-- User profiles table (user preferences and career info)
CREATE TABLE IF NOT EXISTS user_profiles (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    industry TEXT[], -- Array of industries
    skills TEXT[], -- Array of skills
    career_goals TEXT[], -- Array of career goals
    tone TEXT[], -- Array of tone preferences
    interests TEXT[], -- Array of interests
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_profiles_industry ON user_profiles USING GIN(industry);
CREATE INDEX idx_profiles_skills ON user_profiles USING GIN(skills);

-- LinkedIn credentials table (encrypted passwords)
CREATE TABLE IF NOT EXISTS linkedin_credentials (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    encrypted_password BYTEA NOT NULL, -- Binary data for Fernet encryption
    encryption_version VARCHAR(50) DEFAULT 'fernet_v1',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_attempt TIMESTAMP WITH TIME ZONE,
    login_success_count INTEGER DEFAULT 0,
    login_failure_count INTEGER DEFAULT 0
);

CREATE INDEX idx_credentials_email ON linkedin_credentials(email);
CREATE INDEX idx_credentials_updated ON linkedin_credentials(updated_at DESC);

-- Automation stats table (audit trail and analytics)
CREATE TABLE IF NOT EXISTS automation_stats (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL, -- 'post', 'like', 'comment', 'connection', 'message'
    action_count INTEGER DEFAULT 1,
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id UUID, -- Track automation sessions
    metadata JSONB -- Store additional context
);

CREATE INDEX idx_stats_telegram_id ON automation_stats(telegram_id, performed_at DESC);
CREATE INDEX idx_stats_action_type ON automation_stats(action_type, performed_at DESC);
CREATE INDEX idx_stats_session ON automation_stats(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_stats_metadata ON automation_stats USING GIN(metadata) WHERE metadata IS NOT NULL;

-- Promo codes table (marketing and discounts)
CREATE TABLE IF NOT EXISTS promo_codes (
    code VARCHAR(50) PRIMARY KEY,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 0 AND 100),
    max_uses INTEGER NOT NULL,
    current_uses INTEGER DEFAULT 0 CHECK (current_uses <= max_uses),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_promo_active ON promo_codes(active, expires_at);

-- ============================================================================
-- NEW TABLES (Migrated from JSON files)
-- ============================================================================

-- Content strategies table (from content_strategy.json)
CREATE TABLE IF NOT EXISTS content_strategies (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    content_themes TEXT[] NOT NULL DEFAULT '{}',
    posting_frequency VARCHAR(50) DEFAULT 'daily',
    optimal_times TIME[] NOT NULL DEFAULT ARRAY['09:00'::time, '13:00'::time, '17:00'::time],
    content_goals TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_strategies_themes ON content_strategies USING GIN(content_themes);

-- Engagement configs table (from engagement_config.json - user-specific)
CREATE TABLE IF NOT EXISTS engagement_configs (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    relevance_threshold DECIMAL(3,2) DEFAULT 0.5 CHECK (relevance_threshold BETWEEN 0 AND 1),
    hashtags_to_follow TEXT[] DEFAULT '{}',
    keywords_to_engage TEXT[] DEFAULT '{}',
    like_probability DECIMAL(3,2) DEFAULT 1.0 CHECK (like_probability BETWEEN 0 AND 1),
    comment_probability DECIMAL(3,2) DEFAULT 1.0 CHECK (comment_probability BETWEEN 0 AND 1),
    generic_comments TEXT[] DEFAULT '{}',
    ai_provider VARCHAR(50) DEFAULT 'anthropic',
    ai_model VARCHAR(100) DEFAULT 'claude-opus-4-6',
    ai_temperature DECIMAL(3,2) DEFAULT 0.7 CHECK (ai_temperature BETWEEN 0 AND 2),
    ai_max_tokens INTEGER DEFAULT 500,
    max_daily_ai_calls INTEGER DEFAULT 100,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Reply templates table (from reply_templates.json)
CREATE TABLE IF NOT EXISTS reply_templates (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    template_type VARCHAR(50) NOT NULL, -- 'generic', 'question', 'positive', 'keyword'
    template_text TEXT NOT NULL,
    keyword VARCHAR(255), -- For keyword-based templates
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_templates_user ON reply_templates(telegram_id, template_type);
CREATE INDEX idx_templates_keyword ON reply_templates(keyword) WHERE keyword IS NOT NULL;

-- Engaged posts table (from engaged_posts.json - deduplication tracking)
CREATE TABLE IF NOT EXISTS engaged_posts (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    post_id VARCHAR(255) NOT NULL,
    engagement_type VARCHAR(50), -- 'like', 'comment', 'both'
    engaged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    post_content TEXT, -- Cache of post content for analytics
    author_name VARCHAR(255),
    author_title VARCHAR(255),
    relevance_score DECIMAL(3,2),
    UNIQUE(telegram_id, post_id)
);

CREATE INDEX idx_engaged_posts_user ON engaged_posts(telegram_id, engaged_at DESC);
CREATE INDEX idx_engaged_posts_id ON engaged_posts(post_id);
CREATE INDEX idx_engaged_posts_type ON engaged_posts(engagement_type);

-- Commented posts table (from commented_posts.json - prevent duplicate comments)
CREATE TABLE IF NOT EXISTS commented_posts (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    post_id VARCHAR(255) NOT NULL,
    comment_text TEXT,
    commented_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ai_generated BOOLEAN DEFAULT FALSE,
    post_content TEXT,
    author_name VARCHAR(255),
    UNIQUE(telegram_id, post_id)
);

CREATE INDEX idx_commented_posts_user ON commented_posts(telegram_id, commented_at DESC);
CREATE INDEX idx_commented_posts_id ON commented_posts(post_id);
CREATE INDEX idx_commented_posts_ai ON commented_posts(ai_generated) WHERE ai_generated = TRUE;

-- Safety counts table (from safety_counts.json - daily action tracking)
CREATE TABLE IF NOT EXISTS safety_counts (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    action_type VARCHAR(50) NOT NULL, -- 'likes', 'comments', 'connections', 'messages', 'profile_views', 'searches'
    count INTEGER DEFAULT 0,
    UNIQUE(telegram_id, date, action_type)
);

CREATE INDEX idx_safety_counts_user_date ON safety_counts(telegram_id, date DESC);
CREATE INDEX idx_safety_counts_type ON safety_counts(action_type, date DESC);

-- Job seeking configs table (from job_seeking_config.json)
CREATE TABLE IF NOT EXISTS job_seeking_configs (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    target_roles TEXT[] DEFAULT '{}',
    target_locations TEXT[] DEFAULT '{}',
    target_companies TEXT[] DEFAULT '{}',
    avoid_companies TEXT[] DEFAULT '{}',
    target_company_sizes TEXT[] DEFAULT '{}',
    recruiters_per_day INTEGER DEFAULT 10,
    connection_requests_per_day INTEGER DEFAULT 15,
    messages_per_day INTEGER DEFAULT 10,
    prioritize_recruiters BOOLEAN DEFAULT TRUE,
    engage_with_job_posts BOOLEAN DEFAULT TRUE,
    target_hiring_managers BOOLEAN DEFAULT TRUE,
    follow_target_companies BOOLEAN DEFAULT TRUE,
    keywords_to_track TEXT[] DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_seeking_enabled ON job_seeking_configs(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_job_seeking_roles ON job_seeking_configs USING GIN(target_roles);

-- Scheduled content table (new - for scheduled posts)
CREATE TABLE IF NOT EXISTS scheduled_content (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    content_text TEXT NOT NULL,
    theme VARCHAR(255),
    media_url TEXT,
    media_type VARCHAR(50), -- 'image', 'video', null
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'posted', 'failed', 'cancelled'
    ai_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_scheduled_content_user ON scheduled_content(telegram_id, scheduled_time);
CREATE INDEX idx_scheduled_content_status ON scheduled_content(status, scheduled_time);
CREATE INDEX idx_scheduled_content_pending ON scheduled_content(scheduled_time) WHERE status = 'pending';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_linkedin_credentials_updated_at BEFORE UPDATE ON linkedin_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_strategies_updated_at BEFORE UPDATE ON content_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_engagement_configs_updated_at BEFORE UPDATE ON engagement_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_seeking_configs_updated_at BEFORE UPDATE ON job_seeking_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS (Optional - for common queries)
-- ============================================================================

-- View for active subscriptions
CREATE OR REPLACE VIEW active_subscriptions AS
SELECT
    u.telegram_id,
    u.username,
    u.first_name,
    u.subscription_active,
    u.subscription_expires,
    u.stripe_customer_id,
    CASE
        WHEN u.subscription_expires > CURRENT_TIMESTAMP THEN
            EXTRACT(DAY FROM (u.subscription_expires - CURRENT_TIMESTAMP))
        ELSE 0
    END as days_remaining
FROM users u
WHERE u.subscription_active = TRUE
  AND u.subscription_expires > CURRENT_TIMESTAMP;

-- View for user activity summary
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT
    u.telegram_id,
    u.username,
    u.first_name,
    u.last_seen,
    COUNT(DISTINCT CASE WHEN a.action_type = 'post' THEN a.id END) as total_posts,
    COUNT(DISTINCT CASE WHEN a.action_type = 'like' THEN a.id END) as total_likes,
    COUNT(DISTINCT CASE WHEN a.action_type = 'comment' THEN a.id END) as total_comments,
    COUNT(DISTINCT CASE WHEN a.action_type = 'connection' THEN a.id END) as total_connections,
    MAX(a.performed_at) as last_automation_run
FROM users u
LEFT JOIN automation_stats a ON u.telegram_id = a.telegram_id
GROUP BY u.telegram_id, u.username, u.first_name, u.last_seen;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Core user accounts with Telegram and Stripe information';
COMMENT ON TABLE user_profiles IS 'User professional profiles (industry, skills, career goals)';
COMMENT ON TABLE linkedin_credentials IS 'Encrypted LinkedIn login credentials using Fernet';
COMMENT ON TABLE automation_stats IS 'Audit trail of all automation actions performed';
COMMENT ON TABLE promo_codes IS 'Marketing promo codes with usage tracking';
COMMENT ON TABLE content_strategies IS 'User content posting strategies and themes';
COMMENT ON TABLE engagement_configs IS 'Per-user engagement configuration and AI settings';
COMMENT ON TABLE reply_templates IS 'Auto-reply message templates for comments';
COMMENT ON TABLE engaged_posts IS 'Tracking of posts already engaged with (deduplication)';
COMMENT ON TABLE commented_posts IS 'Tracking of posts already commented on (prevent duplicates)';
COMMENT ON TABLE safety_counts IS 'Daily action counts for rate limiting';
COMMENT ON TABLE job_seeking_configs IS 'Job search targeting configuration per user';
COMMENT ON TABLE scheduled_content IS 'AI-generated content scheduled for future posting';

-- ============================================================================
-- JOB SEARCH SCANNER (v2)
-- ============================================================================

-- Extend job_seeking_configs with job scanner fields
ALTER TABLE job_seeking_configs
  ADD COLUMN IF NOT EXISTS notification_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS last_scan_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS resume_keywords TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS scan_keywords TEXT[] DEFAULT '{}';

-- Track jobs already seen/notified (deduplication)
CREATE TABLE IF NOT EXISTS seen_jobs (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    job_id VARCHAR(255) NOT NULL,
    job_title VARCHAR(500),
    company VARCHAR(255),
    location VARCHAR(255),
    job_url TEXT,
    seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(telegram_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_seen_jobs_telegram_id ON seen_jobs(telegram_id);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_seen_at ON seen_jobs(seen_at);

COMMENT ON TABLE seen_jobs IS 'Job listings already notified to users (prevents duplicate notifications)';

-- ============================================================================
-- FACEBOOK BOT (Real Estate Lead Generation)
-- ============================================================================

-- Facebook leads from all sources (Messenger, comments, lead ads)
CREATE TABLE IF NOT EXISTS fb_leads (
    id SERIAL PRIMARY KEY,
    facebook_user_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255),
    full_name VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    budget_min INTEGER,
    budget_max INTEGER,
    property_type VARCHAR(100),  -- HDB/Condo/Landed/Commercial
    intent VARCHAR(50),            -- buy/sell/invest/browse
    timeline VARCHAR(100),         -- urgent/3-6mo/6-12mo/exploring
    location_pref VARCHAR(255),
    lead_score INTEGER DEFAULT 0,  -- 1-10
    status VARCHAR(50) DEFAULT 'new', -- new/contacted/viewing/closed/lost
    source VARCHAR(100),           -- messenger/comment/lead_ad/group
    source_post_id VARCHAR(255),
    first_contact_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_contact_at TIMESTAMP WITH TIME ZONE,
    conversation_state VARCHAR(100), -- main_menu/qualifying/browsing/etc
    conversation_step INTEGER DEFAULT 0,
    notes TEXT,
    agent_telegram_id BIGINT,      -- Which agent owns this lead
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fb_leads_user_id ON fb_leads(facebook_user_id);
CREATE INDEX IF NOT EXISTS idx_fb_leads_status ON fb_leads(status);
CREATE INDEX IF NOT EXISTS idx_fb_leads_score ON fb_leads(lead_score);

-- Messenger conversation history
CREATE TABLE IF NOT EXISTS fb_messages (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES fb_leads(id) ON DELETE CASCADE,
    facebook_user_id VARCHAR(255) NOT NULL,
    direction VARCHAR(10) NOT NULL,    -- sent/received
    message_text TEXT,
    message_type VARCHAR(50),          -- text/quick_reply/button/attachment
    payload VARCHAR(255),              -- Button/quick_reply payload
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fb_messages_lead_id ON fb_messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_fb_messages_user_id ON fb_messages(facebook_user_id);

-- Comment tracking (prevent duplicate replies)
CREATE TABLE IF NOT EXISTS fb_comment_replies (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(255) NOT NULL,
    comment_id VARCHAR(255) UNIQUE NOT NULL,
    commenter_id VARCHAR(255),
    comment_text TEXT,
    reply_text TEXT,
    replied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    dm_sent BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_fb_comment_replies_post_id ON fb_comment_replies(post_id);

-- Follow-up sequences tracking
CREATE TABLE IF NOT EXISTS fb_sequences (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES fb_leads(id) ON DELETE CASCADE,
    sequence_type VARCHAR(50),         -- hot_lead/warm_lead/cold_lead
    current_step INTEGER DEFAULT 0,
    next_send_at TIMESTAMP WITH TIME ZONE,
    completed BOOLEAN DEFAULT FALSE,
    paused BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fb_sequences_next_send ON fb_sequences(next_send_at) WHERE NOT completed AND NOT paused;

-- Agent alerts/notifications
CREATE TABLE IF NOT EXISTS fb_agent_alerts (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES fb_leads(id),
    alert_type VARCHAR(50),            -- hot_lead/new_lead/reply_received/viewing_requested
    alert_message TEXT,
    telegram_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE fb_leads IS 'Facebook Messenger leads from real estate bot';
COMMENT ON TABLE fb_messages IS 'Full conversation history per lead';
COMMENT ON TABLE fb_comment_replies IS 'Track post comments already replied to';
COMMENT ON TABLE fb_sequences IS 'Automated follow-up message sequences';

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_versions (version, description) VALUES
(1, 'Initial PostgreSQL schema migration from SQLite + JSON files');
