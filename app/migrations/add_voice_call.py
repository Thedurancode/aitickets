"""Migration to add voice_call_campaigns and voice_calls tables."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []
    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Create voice_call_campaigns table
        if "voice_call_campaigns" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE voice_call_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    goal VARCHAR(50) NOT NULL,
                    custom_script TEXT,
                    target_all BOOLEAN DEFAULT 0,
                    target_event_id INTEGER,
                    target_segments TEXT,
                    target_customer_ids TEXT,
                    event_context_id INTEGER,
                    discount_percent INTEGER,
                    status VARCHAR(50) DEFAULT 'draft',
                    scheduled_for TIMESTAMP,
                    start_calling_after VARCHAR(5),
                    stop_calling_before VARCHAR(5),
                    timezone VARCHAR(50) DEFAULT 'America/New_York',
                    max_concurrent_calls INTEGER DEFAULT 1,
                    time_between_calls_seconds INTEGER DEFAULT 30,
                    max_retries INTEGER DEFAULT 3,
                    retry_delay_minutes INTEGER DEFAULT 60,
                    allow_voicemail BOOLEAN DEFAULT 1,
                    record_calls BOOLEAN DEFAULT 0,
                    respect_do_not_call BOOLEAN DEFAULT 1,
                    skip_recently_called BOOLEAN DEFAULT 1,
                    skip_days_since_last_call INTEGER DEFAULT 7,
                    total_recipients INTEGER DEFAULT 0,
                    calls_initiated INTEGER DEFAULT 0,
                    calls_completed INTEGER DEFAULT 0,
                    calls_answered INTEGER DEFAULT 0,
                    calls_failed INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (target_event_id) REFERENCES events (id),
                    FOREIGN KEY (event_context_id) REFERENCES events (id)
                )
            """))
            conn.execute(text("CREATE INDEX idx_voice_call_campaigns_status ON voice_call_campaigns (status)"))
            conn.execute(text("CREATE INDEX idx_voice_call_campaigns_scheduled ON voice_call_campaigns (scheduled_for)"))
            results.append("Created voice_call_campaigns table")
        else:
            results.append("voice_call_campaigns table already exists")

        # Create voice_calls table
        if "voice_calls" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE voice_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER,
                    event_goer_id INTEGER NOT NULL,
                    goal VARCHAR(50) NOT NULL,
                    phone_number VARCHAR(50) NOT NULL,
                    call_script TEXT NOT NULL,
                    telnyx_call_id VARCHAR(255),
                    telnyx_status VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'pending',
                    outcome VARCHAR(50),
                    scheduled_for TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_seconds INTEGER,
                    attempt_number INTEGER DEFAULT 1,
                    max_retries INTEGER DEFAULT 3,
                    next_retry_at TIMESTAMP,
                    recording_url TEXT,
                    transcription TEXT,
                    notes TEXT,
                    digits_pressed VARCHAR(10),
                    callback_requested BOOLEAN DEFAULT 0,
                    callback_scheduled_for TIMESTAMP,
                    do_not_call BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (campaign_id) REFERENCES voice_call_campaigns (id),
                    FOREIGN KEY (event_goer_id) REFERENCES event_goers (id)
                )
            """))
            conn.execute(text("CREATE INDEX idx_voice_calls_campaign ON voice_calls (campaign_id)"))
            conn.execute(text("CREATE INDEX idx_voice_calls_event_goer ON voice_calls (event_goer_id)"))
            conn.execute(text("CREATE INDEX idx_voice_calls_status ON voice_calls (status)"))
            conn.execute(text("CREATE INDEX idx_voice_calls_scheduled ON voice_calls (scheduled_for)"))
            conn.execute(text("CREATE INDEX idx_voice_calls_telnyx_id ON voice_calls (telnyx_call_id)"))
            results.append("Created voice_calls table")
        else:
            results.append("voice_calls table already exists")

        conn.commit()

    return results


if __name__ == "__main__":
    results = run_migration()
    for result in results:
        print(result)
