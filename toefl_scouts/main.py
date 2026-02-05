"""Main entry point for TOEFL Reddit Scout"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config
from src.reddit_scraper import RedditScraper
from src.content_analyzer import ContentAnalyzer
from src.discord_notifier import DiscordNotifier
from src.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def meets_post_criteria(post: dict, config: Config) -> bool:
    """Check if post meets filtering criteria
    
    Args:
        post: Post dictionary
        config: Configuration object
        
    Returns:
        True if post meets criteria
    """
    # Check upvotes
    if post['score'] < config.min_upvotes:
        return False
    
    # Check comments
    if post['num_comments'] < config.min_comments:
        return False
    
    # Check keywords (if any configured)
    keywords = config.keywords
    if keywords:
        text = (post['title'] + ' ' + post['selftext']).lower()
        if not any(keyword.lower() in text for keyword in keywords):
            return False
    
    return True


def meets_comment_criteria(comment: dict, config: Config) -> bool:
    """Check if comment meets filtering criteria
    
    Args:
        comment: Comment dictionary
        config: Configuration object
        
    Returns:
        True if comment meets criteria
    """
    # Check score
    if comment['score'] < config.min_comment_score:
        return False
    
    # Skip very short comments
    if len(comment['body']) < 50:
        return False
    
    # Skip deleted/removed comments
    if comment['body'] in ['[deleted]', '[removed]']:
        return False
    
    return True


def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("TOEFL Reddit Scout - Starting")
    logger.info("=" * 60)
    
    try:
        # ═══════════ Initialize ═══════════
        logger.info("Loading configuration...")
        config = Config()
        logger.info(f"Monitoring: {', '.join(config.subreddits)}")
        logger.info(f"TTL: {config.ttl_days} days")
        
        # Initialize modules
        scraper = RedditScraper(user_agent=config.reddit_user_agent)
        
        analyzer = ContentAnalyzer(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
            max_tokens=config.gemini_max_tokens,
            temperature=config.gemini_temperature
        )
        
        notifier = DiscordNotifier(webhook_url=config.discord_webhook_url)
        db = Database(db_path=config.database_path)
        
        # Cleanup old records first (TTL)
        db.cleanup_old_records(days=config.ttl_days)
        
        # ═══════════ Fetch Posts ═══════════
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 1: Fetching Posts")
        logger.info("=" * 60)
        
        # Fetch posts using optimized strategy (hot + rising + top + new)
        posts = scraper.fetch_posts(
            subreddits=config.subreddits,
            time_filter=config.time_filter,
            limit=config.post_limit
        )
        logger.info(f"Fetched {len(posts)} posts")
        
        # Filter 1: Remove posts already pushed to Discord (Database)
        posts = db.filter_new_posts(posts)
        logger.info(f"After DB filter: {len(posts)} posts")
        
        # Filter 2: Apply criteria (upvotes, comments, keywords)
        posts = [p for p in posts if meets_post_criteria(p, config)]
        logger.info(f"After criteria filter: {len(posts)} posts")
        
        # ═══════════ Fetch Comments ═══════════
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 2: Fetching Comments")
        logger.info("=" * 60)
        
        # Fetch comments from remaining posts only
        comments = scraper.fetch_comments_from_posts(
            posts=posts,
            min_score=config.min_comment_score
        )
        logger.info(f"Fetched {len(comments)} comments")
        
        # Apply criteria
        comments = [c for c in comments if meets_comment_criteria(c, config)]
        logger.info(f"After criteria filter: {len(comments)} comments")
        
        # ═══════════ Analyze with Gemini ═══════════
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 3: Gemini Analysis")
        logger.info("=" * 60)
        
        top_posts = []
        top_comments = []
        
        # Analyze posts
        if posts:
            logger.info(f"Analyzing {len(posts)} posts...")
            analyzed_posts = analyzer.analyze_posts_batch(posts)
            top_posts = analyzer.rank_post_opportunities(analyzed_posts)[:config.top_n]
            logger.info(f"TOP {len(top_posts)} posts selected")
        
        # Analyze comments
        if comments:
            logger.info(f"Analyzing {len(comments)} comments...")
            analyzed_comments = analyzer.analyze_comments_batch(comments)
            top_comments = analyzer.rank_comment_opportunities(analyzed_comments)[:config.top_n]
            logger.info(f"TOP {len(top_comments)} comments selected")
        
        # ═══════════ Send to Discord ═══════════
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 4: Discord Notification")
        logger.info("=" * 60)
        
        if top_posts or top_comments:
            notifier.send_daily_report(top_posts, top_comments)
            logger.info(f"Sent: {len(top_posts)} posts, {len(top_comments)} comments")
            
            # Mark as pushed (only posts, since we dedupe by post)
            db.mark_batch_as_pushed(top_posts)
        else:
            logger.info("No new opportunities to push today")
        
        # ═══════════ Summary ═══════════
        logger.info("")
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        
        stats = db.get_stats()
        logger.info(f"Database stats: {stats}")
        logger.info(f"TOP posts pushed: {len(top_posts)}")
        logger.info(f"TOP comments pushed: {len(top_comments)}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("TOEFL Reddit Scout - Completed")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
