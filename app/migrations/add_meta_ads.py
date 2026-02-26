"""Migration to add Meta Ads tables (meta_ad_campaigns, meta_ad_insights)."""
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
        is_sqlite = "sqlite" in str(engine.url)

        # Create meta_ad_campaigns table
        if "meta_ad_campaigns" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE meta_ad_campaigns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        meta_campaign_id VARCHAR(255),
                        meta_ad_set_id VARCHAR(255),
                        meta_ad_id VARCHAR(255),
                        meta_creative_id VARCHAR(255),
                        name VARCHAR(255) NOT NULL,
                        status VARCHAR(20) DEFAULT 'draft',
                        objective VARCHAR(20) DEFAULT 'traffic',
                        budget_type VARCHAR(20) DEFAULT 'daily',
                        budget_cents INTEGER,
                        targeting_radius_miles INTEGER DEFAULT 10,
                        age_min INTEGER,
                        age_max INTEGER,
                        genders VARCHAR(50),
                        interests TEXT,
                        primary_text TEXT,
                        headline VARCHAR(255),
                        description VARCHAR(255),
                        call_to_action VARCHAR(50) DEFAULT 'GET_TICKETS',
                        image_url VARCHAR(500),
                        impressions INTEGER DEFAULT 0,
                        clicks INTEGER DEFAULT 0,
                        spend_cents INTEGER DEFAULT 0,
                        conversions INTEGER DEFAULT 0,
                        error_message TEXT,
                        last_synced_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE meta_ad_campaigns (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        meta_campaign_id VARCHAR(255),
                        meta_ad_set_id VARCHAR(255),
                        meta_ad_id VARCHAR(255),
                        meta_creative_id VARCHAR(255),
                        name VARCHAR(255) NOT NULL,
                        status VARCHAR(20) DEFAULT 'draft',
                        objective VARCHAR(20) DEFAULT 'traffic',
                        budget_type VARCHAR(20) DEFAULT 'daily',
                        budget_cents INTEGER,
                        targeting_radius_miles INTEGER DEFAULT 10,
                        age_min INTEGER,
                        age_max INTEGER,
                        genders VARCHAR(50),
                        interests TEXT,
                        primary_text TEXT,
                        headline VARCHAR(255),
                        description VARCHAR(255),
                        call_to_action VARCHAR(50) DEFAULT 'GET_TICKETS',
                        image_url VARCHAR(500),
                        impressions INTEGER DEFAULT 0,
                        clicks INTEGER DEFAULT 0,
                        spend_cents INTEGER DEFAULT 0,
                        conversions INTEGER DEFAULT 0,
                        error_message TEXT,
                        last_synced_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_id ON meta_ad_campaigns (id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_event_id ON meta_ad_campaigns (event_id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_meta_campaign_id ON meta_ad_campaigns (meta_campaign_id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_meta_ad_set_id ON meta_ad_campaigns (meta_ad_set_id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_meta_ad_id ON meta_ad_campaigns (meta_ad_id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_meta_creative_id ON meta_ad_campaigns (meta_creative_id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_campaigns_status ON meta_ad_campaigns (status)"))
            conn.commit()
            results.append("Created meta_ad_campaigns table")

        # Create meta_ad_insights table
        if "meta_ad_insights" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE meta_ad_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id INTEGER NOT NULL REFERENCES meta_ad_campaigns(id),
                        date VARCHAR(20) NOT NULL,
                        impressions INTEGER DEFAULT 0,
                        clicks INTEGER DEFAULT 0,
                        spend_cents INTEGER DEFAULT 0,
                        conversions INTEGER DEFAULT 0,
                        reach INTEGER DEFAULT 0,
                        ctr_percent INTEGER DEFAULT 0,
                        cpc_cents INTEGER DEFAULT 0,
                        cpa_cents INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE meta_ad_insights (
                        id SERIAL PRIMARY KEY,
                        campaign_id INTEGER NOT NULL REFERENCES meta_ad_campaigns(id),
                        date VARCHAR(20) NOT NULL,
                        impressions INTEGER DEFAULT 0,
                        clicks INTEGER DEFAULT 0,
                        spend_cents INTEGER DEFAULT 0,
                        conversions INTEGER DEFAULT 0,
                        reach INTEGER DEFAULT 0,
                        ctr_percent INTEGER DEFAULT 0,
                        cpc_cents INTEGER DEFAULT 0,
                        cpa_cents INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text("CREATE INDEX ix_meta_ad_insights_id ON meta_ad_insights (id)"))
            conn.execute(text("CREATE INDEX ix_meta_ad_insights_campaign_id ON meta_ad_insights (campaign_id)"))
            conn.commit()
            results.append("Created meta_ad_insights table")

    return results


if __name__ == "__main__":
    run_migration()
