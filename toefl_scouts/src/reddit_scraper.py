"""Reddit scraping module using public JSON API (no auth required)"""

import requests
from typing import List, Dict, Any
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

# Reddit JSON API base URL
REDDIT_BASE_URL = "https://www.reddit.com"

# Rate limiting: Reddit allows ~60 requests per minute
REQUEST_DELAY = 1.0  # seconds between requests


class RedditScraper:
    """Scraper for Reddit posts and comments using public JSON API"""
    
    def __init__(self, user_agent: str = "TOEFL_Scout/1.0"):
        """Initialize scraper
        
        Args:
            user_agent: User agent string (required by Reddit)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent
        })
        self.last_request_time = 0
        
        logger.info("Reddit JSON API scraper initialized")
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def _get_json(self, url: str) -> Dict:
        """Fetch JSON from Reddit API
        
        Args:
            url: Full URL to fetch
            
        Returns:
            JSON response as dictionary
        """
        self._rate_limit()
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {}
    
    # ========== Post Fetching ==========
    
    def fetch_posts(
        self, 
        subreddits: List[str], 
        time_filter: str = 'day',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch posts from specified subreddits using multiple sorting strategies
        
        Strategy: Hot (25%) + Rising (25%) + Top (25%) + New (25%)
        
        Args:
            subreddits: List of subreddit names
            time_filter: Time filter for top posts (hour, day, week, month, year, all)
            limit: Maximum number of posts to fetch per subreddit
            
        Returns:
            List of post dictionaries
        """
        all_posts = {}  # Use dict for deduplication
        per_strategy = limit // 4
        
        for subreddit_name in subreddits:
            try:
                # Fetch from multiple endpoints
                strategies = [
                    ('hot', f"{REDDIT_BASE_URL}/r/{subreddit_name}/hot.json?limit={per_strategy}"),
                    ('rising', f"{REDDIT_BASE_URL}/r/{subreddit_name}/rising.json?limit={per_strategy}"),
                    ('top', f"{REDDIT_BASE_URL}/r/{subreddit_name}/top.json?t={time_filter}&limit={per_strategy}"),
                    ('new', f"{REDDIT_BASE_URL}/r/{subreddit_name}/new.json?limit={per_strategy}")
                ]
                
                counts = {}
                for strategy_name, url in strategies:
                    data = self._get_json(url)
                    posts = self._parse_posts(data)
                    counts[strategy_name] = len(posts)
                    
                    for post in posts:
                        all_posts[post['id']] = post
                
                logger.info(
                    f"r/{subreddit_name}: Fetched {len([p for p in all_posts.values() if p['subreddit'].lower() == subreddit_name.lower()])} unique posts "
                    f"(hot:{counts.get('hot', 0)}, rising:{counts.get('rising', 0)}, "
                    f"top:{counts.get('top', 0)}, new:{counts.get('new', 0)})"
                )
                    
            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
        
        posts_list = list(all_posts.values())
        logger.info(f"Total posts fetched: {len(posts_list)}")
        return posts_list
    
    def _parse_posts(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse posts from Reddit JSON response
        
        Args:
            data: Reddit API response
            
        Returns:
            List of post dictionaries
        """
        posts = []
        
        if not data or 'data' not in data:
            return posts
        
        for item in data['data'].get('children', []):
            if item.get('kind') != 't3':  # t3 = post
                continue
            
            post_data = item.get('data', {})
            
            posts.append({
                'id': post_data.get('id', ''),
                'title': post_data.get('title', ''),
                'selftext': post_data.get('selftext', ''),
                'author': post_data.get('author', '[deleted]'),
                'subreddit': post_data.get('subreddit', ''),
                'score': post_data.get('score', 0),
                'upvote_ratio': post_data.get('upvote_ratio', 0),
                'num_comments': post_data.get('num_comments', 0),
                'created_utc': datetime.fromtimestamp(post_data.get('created_utc', 0)),
                'url': f"https://reddit.com{post_data.get('permalink', '')}",
                'is_self': post_data.get('is_self', True),
                'link_flair_text': post_data.get('link_flair_text', ''),
            })
        
        return posts
    
    # ========== Comment Fetching ==========
    
    def fetch_comments_from_posts(
        self, 
        posts: List[Dict[str, Any]], 
        min_score: int = 3
    ) -> List[Dict[str, Any]]:
        """Fetch comments from a list of posts
        
        Args:
            posts: List of post dictionaries
            min_score: Minimum comment score to include
            
        Returns:
            List of comment dictionaries
        """
        all_comments = []
        
        for post in posts:
            try:
                # Fetch post with comments
                url = f"{REDDIT_BASE_URL}/r/{post['subreddit']}/comments/{post['id']}.json?limit=100"
                data = self._get_json(url)
                
                if not data or len(data) < 2:
                    continue
                
                # data[0] = post, data[1] = comments
                comments = self._parse_comments(data[1], post, min_score)
                
                logger.debug(f"Post {post['id']}: {len(comments)} comments above threshold")
                all_comments.extend(comments)
                
            except Exception as e:
                logger.error(f"Error fetching comments for post {post['id']}: {e}")
        
        logger.info(f"Total comments fetched: {len(all_comments)}")
        return all_comments
    
    def _parse_comments(
        self, 
        data: Dict, 
        post: Dict[str, Any],
        min_score: int = 3,
        depth: int = 0
    ) -> List[Dict[str, Any]]:
        """Parse comments from Reddit JSON response (recursive)
        
        Args:
            data: Reddit API response for comments
            post: Parent post dictionary
            min_score: Minimum score to include
            depth: Current depth in comment tree
            
        Returns:
            List of comment dictionaries
        """
        comments = []
        
        if not data or 'data' not in data:
            return comments
        
        for item in data['data'].get('children', []):
            if item.get('kind') != 't1':  # t1 = comment
                continue
            
            comment_data = item.get('data', {})
            
            # Skip low-score comments
            score = comment_data.get('score', 0)
            if score < min_score:
                continue
            
            # Skip deleted comments
            body = comment_data.get('body', '')
            if body in ['[deleted]', '[removed]', '']:
                continue
            
            comments.append({
                'id': comment_data.get('id', ''),
                'body': body,
                'author': comment_data.get('author', '[deleted]'),
                'score': score,
                'created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)),
                'parent_id': comment_data.get('parent_id', ''),
                'post_id': post['id'],
                'post_title': post['title'],
                'subreddit': post['subreddit'],
                'url': f"https://reddit.com{comment_data.get('permalink', '')}",
                'is_submitter': comment_data.get('is_submitter', False),
                'depth': depth
            })
            
            # Process replies (nested comments)
            replies = comment_data.get('replies', '')
            if replies and isinstance(replies, dict):
                nested = self._parse_comments(replies, post, min_score, depth + 1)
                comments.extend(nested)
        
        return comments
