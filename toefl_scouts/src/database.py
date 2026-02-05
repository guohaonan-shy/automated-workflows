"""Lightweight database module for tracking pushed posts only"""

import sqlite3
from datetime import datetime, timedelta
from typing import Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Database:
    """Lightweight SQLite database for tracking pushed posts
    
    Only stores post IDs that have been pushed to Discord.
    TTL-based cleanup to keep database small.
    """
    
    def __init__(self, db_path: str):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple table: just post_id and pushed_at
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pushed_posts (
                post_id TEXT PRIMARY KEY,
                pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index for cleanup queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pushed_at 
            ON pushed_posts(pushed_at)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def was_pushed(self, post_id: str) -> bool:
        """Check if a post was already pushed to Discord
        
        Args:
            post_id: Reddit post ID
            
        Returns:
            True if post was already pushed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT 1 FROM pushed_posts WHERE post_id = ?',
            (post_id,)
        )
        
        result = cursor.fetchone() is not None
        conn.close()
        
        return result
    
    def mark_as_pushed(self, post_id: str):
        """Mark a post as pushed to Discord
        
        Args:
            post_id: Reddit post ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO pushed_posts (post_id, pushed_at)
            VALUES (?, ?)
        ''', (post_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Marked post {post_id} as pushed")
    
    def mark_batch_as_pushed(self, posts: list):
        """Mark multiple posts as pushed
        
        Args:
            posts: List of post dictionaries (must have 'id' key)
        """
        if not posts:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        data = [(post['id'], now) for post in posts]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO pushed_posts (post_id, pushed_at)
            VALUES (?, ?)
        ''', data)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Marked {len(posts)} posts as pushed")
    
    def get_pushed_ids(self) -> Set[str]:
        """Get all pushed post IDs
        
        Returns:
            Set of post IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT post_id FROM pushed_posts')
        
        ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        return ids
    
    def filter_new_posts(self, posts: list) -> list:
        """Filter out posts that have already been pushed
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            List of posts not yet pushed
        """
        pushed_ids = self.get_pushed_ids()
        new_posts = [p for p in posts if p['id'] not in pushed_ids]
        
        filtered = len(posts) - len(new_posts)
        if filtered > 0:
            logger.info(f"Filtered out {filtered} already-pushed posts")
        
        return new_posts
    
    def cleanup_old_records(self, days: int = 3) -> int:
        """Delete records older than specified days
        
        Args:
            days: Number of days to keep (default: 3)
            
        Returns:
            Number of deleted records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute(
            'DELETE FROM pushed_posts WHERE pushed_at < ?',
            (cutoff_date,)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        
        # Vacuum to reclaim space
        cursor.execute('VACUUM')
        
        conn.close()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old records (older than {days} days)")
        
        return deleted
    
    def get_stats(self) -> dict:
        """Get database statistics
        
        Returns:
            Dictionary with stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM pushed_posts')
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {'total': total}
