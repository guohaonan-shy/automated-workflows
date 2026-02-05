"""Configuration test script - verify all API keys and settings"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_reddit_json_api(config: Config) -> bool:
    """Test Reddit JSON API access (no auth required)"""
    try:
        # Test fetching from r/TOEFL
        url = "https://www.reddit.com/r/TOEFL/hot.json?limit=3"
        headers = {'User-Agent': config.reddit_user_agent}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        post_count = len(data.get('data', {}).get('children', []))
        
        logger.info(f"✓ Reddit JSON API: Connected (fetched {post_count} posts from r/TOEFL)")
        return True
    except Exception as e:
        logger.error(f"✗ Reddit JSON API: Failed - {e}")
        return False


def test_gemini_api(config: Config) -> bool:
    """Test Gemini API connection"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.gemini_api_key)
        model = genai.GenerativeModel(config.gemini_model)
        
        # Test with a simple prompt
        response = model.generate_content("Say 'Hello'")
        logger.info(f"✓ Gemini API: Connected ({config.gemini_model})")
        return True
    except Exception as e:
        logger.error(f"✗ Gemini API: Failed - {e}")
        return False


def test_discord_webhook(config: Config) -> bool:
    """Test Discord webhook"""
    try:
        payload = {
            "content": "🧪 **TOEFL Scout 配置测试**\n\n这是一条测试消息，说明你的 Discord Webhook 配置正确！"
        }
        response = requests.post(config.discord_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("✓ Discord Webhook: Message sent successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Discord Webhook: Failed - {e}")
        return False


def test_database(config: Config) -> bool:
    """Test database initialization"""
    try:
        from src.database import Database
        db = Database(config.database_path)
        stats = db.get_stats()
        logger.info(f"✓ Database: Initialized (posts: {stats.get('total', 0)})")
        return True
    except Exception as e:
        logger.error(f"✗ Database: Failed - {e}")
        return False


def main():
    """Run all configuration tests"""
    print("=" * 60)
    print("TOEFL Reddit Scout - Configuration Test")
    print("=" * 60)
    print()
    
    # Load configuration
    try:
        config = Config()
        logger.info("✓ Configuration file loaded successfully")
        logger.info(f"  Subreddits: {', '.join(config.subreddits)}")
        logger.info(f"  TTL days: {config.ttl_days}")
    except Exception as e:
        logger.error(f"✗ Failed to load configuration: {e}")
        sys.exit(1)
    
    print()
    print("Testing API connections...")
    print("-" * 60)
    
    # Run tests
    results = {
        "Reddit JSON API": test_reddit_json_api(config),
        "Gemini API": test_gemini_api(config),
        "Discord Webhook": test_discord_webhook(config),
        "Database": test_database(config)
    }
    
    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20} {status}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("🎉 所有配置测试通过！你可以运行 main.py 了。")
        sys.exit(0)
    else:
        print()
        print("⚠️  部分测试失败，请检查上面的错误信息并修复配置。")
        sys.exit(1)


if __name__ == "__main__":
    main()
