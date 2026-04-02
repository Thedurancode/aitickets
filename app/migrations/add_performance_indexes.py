"""
Add Performance Indexes Migration

Adds missing database indexes to improve query performance and prevent N+1 issues.
"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """Add performance indexes."""
    with engine.connect() as connection:
        print("Adding performance indexes...")

        # Affiliate referrals - for conversion tracking queries
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_referrals_converted "
                "ON affiliate_referrals(converted_at)"
            ))
            print("✅ Added index on affiliate_referrals.converted_at")
        except Exception as e:
            print(f"⚠️  Index on affiliate_referrals.converted_at may already exist: {e}")

        # Loyalty transactions - for time-based queries
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_loyalty_trans_created "
                "ON loyalty_transactions(created_at)"
            ))
            print("✅ Added index on loyalty_transactions.created_at")
        except Exception as e:
            print(f"⚠️  Index on loyalty_transactions.created_at may already exist: {e}")

        # Group purchases - for expiration checks
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_group_expires "
                "ON group_purchases(expires_at)"
            ))
            print("✅ Added index on group_purchases.expires_at")
        except Exception as e:
            print(f"⚠️  Index on group_purchases.expires_at may already exist: {e}")

        # Group contributions - for payment status queries
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_contribution_paid "
                "ON group_contributions(paid)"
            ))
            print("✅ Added index on group_contributions.paid")
        except Exception as e:
            print(f"⚠️  Index on group_contributions.paid may already exist: {e}")

        # Composite index for active affiliate referrals
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_referrals_affiliate_converted "
                "ON affiliate_referrals(affiliate_id, converted_at)"
            ))
            print("✅ Added composite index on affiliate_referrals(affiliate_id, converted_at)")
        except Exception as e:
            print(f"⚠️  Composite index may already exist: {e}")

        # Audit logs - for searching by entity
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_audit_entity "
                "ON audit_logs(entity_type, entity_id)"
            ))
            print("✅ Added composite index on audit_logs(entity_type, entity_id)")
        except Exception as e:
            print(f"⚠️  Audit logs index may already exist: {e}")

        # Audit logs - for user action history
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_audit_user_action "
                "ON audit_logs(user_id, action)"
            ))
            print("✅ Added composite index on audit_logs(user_id, action)")
        except Exception as e:
            print(f"⚠️  Audit user index may already exist: {e}")

        connection.commit()
        print("✅ Performance indexes migration completed successfully")


def downgrade():
    """Remove performance indexes."""
    with engine.connect() as connection:
        indexes = [
            "idx_referrals_converted",
            "idx_loyalty_trans_created",
            "idx_group_expires",
            "idx_contribution_paid",
            "idx_referrals_affiliate_converted",
            "idx_audit_entity",
            "idx_audit_user_action"
        ]

        for index in indexes:
            try:
                connection.execute(text(f"DROP INDEX IF EXISTS {index}"))
                print(f"✅ Dropped index {index}")
            except Exception as e:
                print(f"⚠️  Failed to drop {index}: {e}")

        connection.commit()
        print("✅ Performance indexes rollback completed")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
