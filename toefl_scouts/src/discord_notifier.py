"""Discord notification module for sending daily reports"""

import requests
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send notifications to Discord via webhook"""
    
    def __init__(self, webhook_url: str):
        """Initialize Discord webhook
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        logger.info("Discord notifier initialized")
    
    def send_daily_report(
        self, 
        top_posts: List[Dict[str, Any]], 
        top_comments: List[Dict[str, Any]]
    ):
        """Send daily report with top posts and comments
        
        Args:
            top_posts: List of top ranked posts
            top_comments: List of top ranked comments
        """
        if not top_posts and not top_comments:
            logger.info("No content to send")
            return
        
        # Build report message
        message = self._build_report_message(top_posts, top_comments)
        
        # Send to Discord (split if too long)
        self._send_message(message)
        
        logger.info(
            f"Sent Discord report: {len(top_posts)} posts, {len(top_comments)} comments"
        )
    
    def _build_report_message(
        self, 
        posts: List[Dict[str, Any]], 
        comments: List[Dict[str, Any]]
    ) -> str:
        """Build formatted report message
        
        Args:
            posts: List of top posts
            comments: List of top comments
            
        Returns:
            Formatted message string
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        message = f"""━━━━━━━━━━━━━━━━━━━━━━━
📊 **TOEFL Reddit 每日机会报告**
📅 {date_str}
━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        # Add posts section
        if posts:
            message += """═══════════════════════
📌 **TOP 10 优质帖子**
═══════════════════════

"""
            for i, post in enumerate(posts[:10], 1):
                message += self._format_post(post, i)
                message += "\n---\n\n"
        
        # Add comments section
        if comments:
            message += """═══════════════════════
💬 **TOP 10 优质评论**
═══════════════════════

"""
            for i, comment in enumerate(comments[:10], 1):
                message += self._format_comment(comment, i)
                message += "\n---\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += "✨ 祝你获得更多社区影响力！"
        
        return message
    
    def _format_post(self, post: Dict[str, Any], rank: int) -> str:
        """Format a single post
        
        Args:
            post: Post dictionary with analysis
            rank: Rank number
            
        Returns:
            Formatted string
        """
        score = post.get('score', 0)
        product_fit = post.get('product_fit', 'medium')
        reply_strategy = post.get('reply_strategy', {})
        
        # Product fit emoji
        fit_emoji = {
            'high': '🎯',
            'medium': '🔸',
            'low': '◽'
        }.get(product_fit, '🔸')
        
        message = f"""**【#{rank}】⭐ 评分: {score:.1f}/10**
📝 **{post['title']}**
🏷️ 主题: {post.get('topic', 'General')}
🔥 热度: {post['score']}↑, {post['num_comments']}💬
⏰ 发帖: {self._format_time_ago(post['created_utc'])}
{fit_emoji} 契合度: {product_fit}

💡 **回复策略:**
"""
        
        # Add key points
        key_points = reply_strategy.get('key_points', [])
        for i, point in enumerate(key_points[:4], 1):
            message += f"{i}. {point}\n"
        
        # Add angle and product mention
        if 'angle' in reply_strategy:
            message += f"\n📐 切入角度: {reply_strategy['angle']}\n"
        
        if 'product_mention' in reply_strategy:
            message += f"🎁 产品植入: {reply_strategy['product_mention']}\n"
        
        # Add link
        message += f"\n🔗 [直达帖子]({post['url']})"
        
        return message
    
    def _format_comment(self, comment: Dict[str, Any], rank: int) -> str:
        """Format a single comment
        
        Args:
            comment: Comment dictionary with analysis
            rank: Rank number
            
        Returns:
            Formatted string
        """
        score = comment.get('score', 0)
        opportunity_type = comment.get('opportunity_type', 'supplement')
        product_fit = comment.get('product_fit', 'medium')
        reply_strategy = comment.get('reply_strategy', {})
        
        # Opportunity type emoji
        type_emoji = {
            'supplement': '➕',
            'correct': '✏️',
            'alternative': '🔄',
            'disagree': '💭'
        }.get(opportunity_type, '💬')
        
        # Product fit emoji
        fit_emoji = {
            'high': '🎯',
            'medium': '🔸',
            'low': '◽'
        }.get(product_fit, '🔸')
        
        # Truncate comment body
        body_preview = comment['body'][:150]
        if len(comment['body']) > 150:
            body_preview += "..."
        
        message = f"""**【#{rank}】⭐ 评分: {score:.1f}/10**
📍 **原帖:** "{comment['post_title'][:60]}..."
💬 评论: "{body_preview}"
👤 作者: u/{comment['author']}
🔥 热度: {comment['score']}↑
⏰ 评论: {self._format_time_ago(comment['created_utc'])}
{fit_emoji} 契合度: {product_fit}

{type_emoji} **回复机会:** {opportunity_type}
💭 原因: {comment.get('reason', 'N/A')[:100]}

💡 **回复要点:**
"""
        
        # Add key points
        key_points = reply_strategy.get('key_points', [])
        for i, point in enumerate(key_points[:4], 1):
            message += f"{i}. {point}\n"
        
        # Add angle
        if 'angle' in reply_strategy:
            message += f"\n📐 策略: {reply_strategy['angle']}\n"
        
        # Add link
        message += f"\n🔗 [直达评论]({comment['url']})"
        
        return message
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as time ago string
        
        Args:
            dt: Datetime object
            
        Returns:
            Time ago string (e.g., "3小时前", "2天前")
        """
        now = datetime.now()
        diff = now - dt
        
        hours = diff.total_seconds() / 3600
        
        if hours < 1:
            return f"{int(diff.total_seconds() / 60)}分钟前"
        elif hours < 24:
            return f"{int(hours)}小时前"
        else:
            return f"{int(hours / 24)}天前"
    
    def _send_message(self, message: str):
        """Send message to Discord webhook
        
        Args:
            message: Message content
        """
        # Discord has a 2000 character limit per message
        # Split if necessary
        chunks = self._split_message(message, 1900)
        
        for chunk in chunks:
            payload = {
                "content": chunk
            }
            
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send Discord message: {e}")
    
    def _split_message(self, message: str, max_length: int = 1900) -> List[str]:
        """Split long message into chunks
        
        Args:
            message: Full message
            max_length: Maximum length per chunk
            
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        lines = message.split('\n')
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
