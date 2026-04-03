"""
Migration: Add Weather Intelligence & Expert Features
Created: 2025-01-XX
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Boolean, Text
from app.database import Base, engine


def upgrade():
    """Add weather monitoring, predictions, and recommendations tables."""
    from sqlalchemy import text

    with engine.begin() as conn:
        # Weather Forecasts table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather_forecasts (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                forecast_date DATE NOT NULL,
                temperature_high FLOAT,
                temperature_low FLOAT,
                precipitation_probability FLOAT,
                precipitation_amount FLOAT,
                conditions VARCHAR(100),
                wind_speed FLOAT,
                humidity FLOAT,
                api_response TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_weather_event_date
            ON weather_forecasts(event_id, forecast_date)
        """))

        # Weather Alerts table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather_alerts (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                old_value FLOAT,
                new_value FLOAT,
                message TEXT NOT NULL,
                notified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_weather_alerts_event
            ON weather_alerts(event_id, created_at)
        """))

        # Sales Predictions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales_predictions (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                prediction_date TIMESTAMP NOT NULL,
                predicted_tickets_sold INTEGER,
                predicted_revenue INTEGER,
                confidence_score FLOAT,
                sellout_probability FLOAT,
                days_to_sellout FLOAT,
                model_version VARCHAR(50),
                feature_importance TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_predictions_event
            ON sales_predictions(event_id, prediction_date)
        """))

        # AI Recommendations table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                id INTEGER PRIMARY KEY,
                event_id INTEGER,
                recommendation_type VARCHAR(50) NOT NULL,
                priority VARCHAR(20) NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reasoning TEXT,
                expected_impact TEXT,
                action_items TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                implemented_at TIMESTAMP,
                result_data TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_recommendations_status
            ON ai_recommendations(status, priority, created_at)
        """))

        # Budget Optimization Log table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS budget_optimization_log (
                id INTEGER PRIMARY KEY,
                event_id INTEGER,
                optimization_type VARCHAR(50) NOT NULL,
                from_channel VARCHAR(50),
                to_channel VARCHAR(50),
                amount_moved INTEGER,
                reason TEXT,
                expected_improvement TEXT,
                actual_improvement TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_budget_opt_event
            ON budget_optimization_log(event_id, created_at)
        """))

        print("✅ Added weather intelligence, predictions, recommendations, and optimization tables")


def downgrade():
    """Remove expert feature tables."""
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS budget_optimization_log"))
        conn.execute(text("DROP TABLE IF EXISTS ai_recommendations"))
        conn.execute(text("DROP TABLE IF EXISTS sales_predictions"))
        conn.execute(text("DROP TABLE IF EXISTS weather_alerts"))
        conn.execute(text("DROP TABLE IF EXISTS weather_forecasts"))
        print("✅ Removed expert feature tables")


def run_migration():
    """Run the migration (standard interface)."""
    upgrade()


if __name__ == "__main__":
    run_migration()
