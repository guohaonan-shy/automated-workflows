"""Configuration management for TOEFL Reddit Scout"""

import os
import yaml
from pathlib import Path
from typing import List, Any
from dotenv import load_dotenv

class Config:
    """Configuration loader and validator"""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration
        
        Args:
            config_path: Path to config.yaml file. If None, uses default path.
        """
        # Load environment variables
        load_dotenv()
        
        # Load YAML config
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Validate required environment variables
        self._validate_env_vars()
    
    def _validate_env_vars(self):
        """Validate that all required environment variables are set"""
        required_vars = [
            'GEMINI_API_KEY',
            'DISCORD_WEBHOOK_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please set them in .env file or environment."
            )
    
    # ========== Reddit Config ==========
    
    @property
    def reddit_user_agent(self) -> str:
        """User agent for Reddit API requests"""
        return os.getenv('REDDIT_USER_AGENT', 'TOEFL_Scout/1.0')
    
    @property
    def subreddits(self) -> List[str]:
        """List of subreddits to monitor"""
        return self.config.get('reddit', {}).get('subreddits', ['TOEFL', 'ToeflAdvice'])
    
    @property
    def post_limit(self) -> int:
        """Maximum number of posts to fetch per subreddit"""
        return self.config.get('reddit', {}).get('post_limit', 50)
    
    @property
    def time_filter(self) -> str:
        """Time filter for top posts"""
        return self.config.get('reddit', {}).get('time_filter', 'day')
    
    # ========== Gemini Config ==========
    
    @property
    def gemini_api_key(self) -> str:
        """Google Gemini API key"""
        return os.getenv('GEMINI_API_KEY')
    
    @property
    def gemini_model(self) -> str:
        """Gemini model name"""
        return self.config.get('gemini', {}).get('model', 'gemini-1.5-flash')
    
    @property
    def gemini_max_tokens(self) -> int:
        """Maximum tokens for Gemini response"""
        return self.config.get('gemini', {}).get('max_tokens', 2048)
    
    @property
    def gemini_temperature(self) -> float:
        """Temperature for Gemini generation"""
        return self.config.get('gemini', {}).get('temperature', 0.3)
    
    # ========== Filter Config ==========
    
    @property
    def min_upvotes(self) -> int:
        """Minimum upvotes for posts"""
        return self.config.get('filters', {}).get('min_upvotes', 5)
    
    @property
    def min_comments(self) -> int:
        """Minimum comments for posts"""
        return self.config.get('filters', {}).get('min_comments', 2)
    
    @property
    def min_comment_score(self) -> int:
        """Minimum score for comments"""
        return self.config.get('filters', {}).get('min_comment_score', 3)
    
    @property
    def keywords(self) -> List[str]:
        """Keywords to filter posts"""
        return self.config.get('filters', {}).get('keywords', [])
    
    # ========== Database Config ==========
    
    @property
    def ttl_days(self) -> int:
        """TTL for pushed posts in days (default: 3)"""
        return self.config.get('database', {}).get('ttl_days', 3)
    
    @property
    def database_path(self) -> str:
        """Path to SQLite database
        
        On Railway: uses /app/data (Volume mount point)
        Local: uses ./data relative to project
        """
        import os
        
        # Railway Volume mount point
        if os.path.exists('/app/data'):
            db_path = Path('/app/data/pushed_posts.db')
        else:
            # Local development
            db_path = Path(__file__).parent.parent / "data" / "pushed_posts.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(db_path)
    
    # ========== Discord Config ==========
    
    @property
    def discord_webhook_url(self) -> str:
        """Discord webhook URL"""
        return os.getenv('DISCORD_WEBHOOK_URL')
    
    # ========== Output Config ==========
    
    @property
    def top_n(self) -> int:
        """Number of top opportunities to return"""
        return self.config.get('output', {}).get('top_n', 10)
    
    # ========== Utility ==========
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
