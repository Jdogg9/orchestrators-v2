#!/usr/bin/env python3
"""
File: scripts/sqlite_maintenance.py
Purpose: SQLite database maintenance (VACUUM, TTL enforcement, pruning)
Usage: python3 sqlite_maintenance.py [--dry-run]
Schedule: Daily at 03:00 AM via aimee-sqlite-maintenance.timer
"""

import sys
import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
INSTANCE_DIR = REPO_ROOT / "instance"

# Environment variables (with defaults)
MAINTENANCE_ENABLED = int(os.getenv("SQLITE_MAINTENANCE_ENABLED", "0"))
VACUUM_ENABLED = int(os.getenv("SQLITE_VACUUM_ENABLED", "1"))

# Per-database TTL configuration (days, 0=disabled)
TTL_CONFIG = {
    "agent9_interactions.db": {
        "ttl_days": int(os.getenv("SQLITE_TTL_AGENT9_DAYS", "0")),
        "table": "interactions",
        "timestamp_column": "timestamp",
    },
    "api_proxy_interactions.db": {
        "ttl_days": int(os.getenv("SQLITE_TTL_API_PROXY_DAYS", "0")),
        "table": "requests",
        "timestamp_column": "created_at",
    },
    "usage_telemetry.db": {
        "ttl_days": int(os.getenv("SQLITE_TTL_USAGE_TELEMETRY_DAYS", "30")),
        "table": "usage_events",
        "timestamp_column": "created_at",
    },
}

# Recall frame limits (0=disabled)
RECALL_FRAMES_TTL_DAYS = int(os.getenv("SQLITE_TTL_RECALL_FRAMES_DAYS", "0"))
RECALL_MAX_DISK_MB = int(os.getenv("SQLITE_MAX_RECALL_DISK_MB", "0"))

# Databases to VACUUM (always safe, no data loss)
VACUUM_DATABASES = [
    "aimee_core.db",
    "recall_memory.db",
    "agent9_interactions.db",
    "api_proxy_interactions.db",
    "usage_telemetry.db",
    "model_switches.db",
]

# ============================================================================
# Logging
# ============================================================================

def log_json(event: str, **kwargs):
    """Log structured JSON event"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        **kwargs
    }
    print(json.dumps(log_data), flush=True)

def log_error(message: str, **kwargs):
    """Log error event"""
    log_json("MAINTENANCE_ERROR", message=message, **kwargs)
    print(f"ERROR: {message}", file=sys.stderr)

# ============================================================================
# Database Operations
# ============================================================================

def get_db_size_mb(db_path: Path) -> float:
    """Get database file size in MB"""
    if not db_path.exists():
        return 0.0
    return db_path.stat().st_size / (1024 * 1024)

def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    """Get row count for a table"""
    try:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.Error:
        return 0

def vacuum_database(db_path: Path, dry_run: bool = False) -> Tuple[bool, float]:
    """
    VACUUM database to reclaim space
    Returns: (success, freed_mb)
    """
    if not db_path.exists():
        log_json("VACUUM_SKIP", db=db_path.name, reason="file_not_found")
        return True, 0.0
    
    size_before = get_db_size_mb(db_path)
    
    if dry_run:
        log_json("VACUUM_DRY_RUN", db=db_path.name, size_mb=round(size_before, 2))
        return True, 0.0
    
    try:
        conn = sqlite3.connect(db_path)
        log_json("VACUUM_START", db=db_path.name)
        
        # VACUUM (reclaim deleted space)
        conn.execute("VACUUM")
        
        # PRAGMA optimize (update query planner stats)
        conn.execute("PRAGMA optimize")
        
        conn.close()
        
        size_after = get_db_size_mb(db_path)
        freed_mb = size_before - size_after
        
        log_json("VACUUM_SUCCESS", 
                 db=db_path.name, 
                 size_before_mb=round(size_before, 2),
                 size_after_mb=round(size_after, 2),
                 freed_mb=round(freed_mb, 2))
        
        return True, freed_mb
    
    except sqlite3.Error as e:
        log_error(f"VACUUM failed for {db_path.name}", error=str(e))
        return False, 0.0

def enforce_ttl(db_path: Path, config: Dict, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Enforce TTL by deleting expired rows
    Returns: (success, deleted_count)
    """
    if not db_path.exists():
        return True, 0
    
    ttl_days = config["ttl_days"]
    if ttl_days <= 0:
        log_json("TTL_SKIP", db=db_path.name, reason="ttl_disabled")
        return True, 0
    
    table = config["table"]
    timestamp_col = config["timestamp_column"]
    cutoff_date = (datetime.utcnow() - timedelta(days=ttl_days)).isoformat()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Count rows before
        rows_before = get_row_count(conn, table)
        
        # Find expired rows
        cursor = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {timestamp_col} < ?",
            (cutoff_date,)
        )
        expired_count = cursor.fetchone()[0]
        
        if expired_count == 0:
            log_json("TTL_NO_EXPIRED", db=db_path.name, ttl_days=ttl_days)
            conn.close()
            return True, 0
        
        if dry_run:
            log_json("TTL_DRY_RUN", 
                     db=db_path.name, 
                     ttl_days=ttl_days,
                     expired_count=expired_count,
                     action="would_delete")
            conn.close()
            return True, expired_count
        
        # Delete expired rows (with transaction)
        log_json("TTL_DELETE_START", 
                 db=db_path.name, 
                 ttl_days=ttl_days,
                 expired_count=expired_count)
        
        conn.execute("BEGIN")
        conn.execute(
            f"DELETE FROM {table} WHERE {timestamp_col} < ?",
            (cutoff_date,)
        )
        conn.commit()
        
        # Count rows after
        rows_after = get_row_count(conn, table)
        deleted_count = rows_before - rows_after
        
        conn.close()
        
        log_json("TTL_DELETE_SUCCESS", 
                 db=db_path.name,
                 deleted_count=deleted_count,
                 rows_remaining=rows_after)
        
        return True, deleted_count
    
    except sqlite3.Error as e:
        log_error(f"TTL enforcement failed for {db_path.name}", error=str(e))
        return False, 0

def prune_recall_frames(dry_run: bool = False) -> Tuple[bool, int]:
    """
    Prune recall_memory.db frames by age or disk usage
    Returns: (success, deleted_count)
    """
    db_path = INSTANCE_DIR / "recall_memory.db"
    
    if not db_path.exists():
        return True, 0
    
    # Check if pruning is enabled
    if RECALL_FRAMES_TTL_DAYS <= 0 and RECALL_MAX_DISK_MB <= 0:
        log_json("RECALL_PRUNE_SKIP", reason="pruning_disabled")
        return True, 0
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Count frames before
        frames_before = get_row_count(conn, "frames")
        db_size_mb = get_db_size_mb(db_path)
        
        deleted_count = 0
        
        # Prune by age (if enabled)
        if RECALL_FRAMES_TTL_DAYS > 0:
            cutoff_date = (datetime.utcnow() - timedelta(days=RECALL_FRAMES_TTL_DAYS)).isoformat()
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM frames WHERE timestamp < ?",
                (cutoff_date,)
            )
            expired_count = cursor.fetchone()[0]
            
            if expired_count > 0:
                if dry_run:
                    log_json("RECALL_PRUNE_DRY_RUN",
                             reason="age",
                             ttl_days=RECALL_FRAMES_TTL_DAYS,
                             expired_count=expired_count)
                else:
                    log_json("RECALL_PRUNE_START", reason="age", count=expired_count)
                    conn.execute("BEGIN")
                    conn.execute("DELETE FROM frames WHERE timestamp < ?", (cutoff_date,))
                    conn.commit()
                    deleted_count += expired_count
        
        # Prune by disk usage (if enabled and still over limit)
        if RECALL_MAX_DISK_MB > 0 and db_size_mb > RECALL_MAX_DISK_MB:
            # Calculate how many frames to delete (rough estimate)
            bytes_to_free = (db_size_mb - RECALL_MAX_DISK_MB) * 1024 * 1024
            avg_frame_size = db_path.stat().st_size / max(frames_before, 1)
            frames_to_delete = int(bytes_to_free / avg_frame_size) + 100  # +100 margin
            
            if frames_to_delete > 0:
                if dry_run:
                    log_json("RECALL_PRUNE_DRY_RUN",
                             reason="disk",
                             current_mb=round(db_size_mb, 2),
                             max_mb=RECALL_MAX_DISK_MB,
                             frames_to_delete=frames_to_delete)
                else:
                    log_json("RECALL_PRUNE_START", 
                             reason="disk", 
                             count=frames_to_delete)
                    conn.execute("BEGIN")
                    conn.execute(
                        "DELETE FROM frames WHERE id IN "
                        "(SELECT id FROM frames ORDER BY timestamp ASC LIMIT ?)",
                        (frames_to_delete,)
                    )
                    conn.commit()
                    deleted_count += frames_to_delete
        
        # Count frames after
        frames_after = get_row_count(conn, "frames")
        actual_deleted = frames_before - frames_after
        
        conn.close()
        
        if actual_deleted > 0:
            log_json("RECALL_PRUNE_SUCCESS",
                     deleted_count=actual_deleted,
                     frames_remaining=frames_after)
        
        return True, actual_deleted
    
    except sqlite3.Error as e:
        log_error("Recall frame pruning failed", error=str(e))
        return False, 0

# ============================================================================
# Main Execution
# ============================================================================

def main():
    dry_run = "--dry-run" in sys.argv
    
    # Determine mode
    if not MAINTENANCE_ENABLED:
        mode = "dry_run"
    else:
        mode = "execute" if not dry_run else "dry_run_explicit"
    
    log_json("MAINTENANCE_START", 
             mode=mode,
             vacuum_enabled=bool(VACUUM_ENABLED),
             maintenance_enabled=bool(MAINTENANCE_ENABLED))
    
    # Track results
    vacuum_success = 0
    vacuum_failed = 0
    total_freed_mb = 0.0
    ttl_success = 0
    ttl_failed = 0
    total_deleted = 0
    
    # Phase 1: VACUUM databases (always safe, no data loss)
    if VACUUM_ENABLED:
        for db_name in VACUUM_DATABASES:
            db_path = INSTANCE_DIR / db_name
            success, freed_mb = vacuum_database(db_path, dry_run=(not MAINTENANCE_ENABLED or dry_run))
            if success:
                vacuum_success += 1
                total_freed_mb += freed_mb
            else:
                vacuum_failed += 1
    
    # Phase 2: TTL enforcement (opt-in per database)
    if MAINTENANCE_ENABLED and not dry_run:
        for db_name, config in TTL_CONFIG.items():
            if config["ttl_days"] > 0:
                db_path = INSTANCE_DIR / db_name
                success, deleted_count = enforce_ttl(db_path, config, dry_run=False)
                if success:
                    ttl_success += 1
                    total_deleted += deleted_count
                else:
                    ttl_failed += 1
    else:
        # Dry-run: show what would be deleted
        for db_name, config in TTL_CONFIG.items():
            if config["ttl_days"] > 0:
                db_path = INSTANCE_DIR / db_name
                enforce_ttl(db_path, config, dry_run=True)
    
    # Phase 3: Recall frame pruning (opt-in)
    if RECALL_FRAMES_TTL_DAYS > 0 or RECALL_MAX_DISK_MB > 0:
        success, deleted_count = prune_recall_frames(dry_run=(not MAINTENANCE_ENABLED or dry_run))
        if success:
            total_deleted += deleted_count
    
    # Summary
    log_json("MAINTENANCE_COMPLETE",
             mode=mode,
             vacuum_success=vacuum_success,
             vacuum_failed=vacuum_failed,
             total_freed_mb=round(total_freed_mb, 2),
             ttl_success=ttl_success,
             ttl_failed=ttl_failed,
             total_deleted=total_deleted)
    
    # Exit code
    if vacuum_failed > 0 or ttl_failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
