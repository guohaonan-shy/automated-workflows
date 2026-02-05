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
📊 **TOEFL Reddit Daily Report**
📅 {date_str}
━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        # Add posts section
        if posts:
            message += """═══════════════════════
📌 **TOP Posts**
═══════════════════════

"""
            for i, post in enumerate(posts[:10], 1):
                message += self._format_post(post, i)
                message += "\n---\n\n"
        
        # Add comments section
        if comments:
            message += """═══════════════════════
💬 **TOP Comments**
═══════════════════════

"""
            for i, comment in enumerate(comments[:10], 1):
                message += self._format_comment(comment, i)
                message += "\n---\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += "✨ Good luck with your outreach!"
        
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
        reply_candidates = post.get('reply_candidates', [])
        
        # Product fit emoji
        fit_emoji = {
            'high': '🎯',
            'medium': '🔸',
            'low': '◽'
        }.get(product_fit, '🔸')
        
        message = f"""**【#{rank}】⭐ Score: {score:.1f}/10**
📝 **{post['title']}**
🏷️ Topic: {post.get('topic', 'General')}
🔥 Engagement: {post['score']}↑, {post['num_comments']}💬
⏰ Posted: {self._format_time_ago(post['created_utc'])}
{fit_emoji} Product Fit: {product_fit}

"""
        
        # Add reply candidates
        if reply_candidates:
            message += "📋 **Reply Candidates (Copy & Paste Ready):**\n\n"
            
            for i, candidate in enumerate(reply_candidates, 1):
                style = candidate.get('style', f'Option {i}')
                tone = candidate.get('tone', '')
                draft = candidate.get('draft', '')
                why = candidate.get('why', '')
                
                message += f"**【{i}】{style}** ({tone})\n"
                message += f"💭 *Why this: {why}*\n"
                message += f"```\n{draft}\n```\n\n"
        
        # Add link
        message += f"🔗 [Go to Post]({post['url']})"
        
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
        reply_candidates = comment.get('reply_candidates', [])
        
        # Opportunity type emoji & label
        type_info = {
            'supplement': ('➕', 'Add Value'),
            'correct': ('✏️', 'Correct Info'),
            'alternative': ('🔄', 'Offer Alternative'),
            'disagree': ('💭', 'Politely Disagree')
        }.get(opportunity_type, ('💬', 'Reply'))
        
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
        
        message = f"""**【#{rank}】⭐ Score: {score:.1f}/10**
📍 **Original Post:** "{comment['post_title'][:60]}..."
💬 Comment: "{body_preview}"
👤 Author: u/{comment['author']}
🔥 Engagement: {comment['score']}↑
⏰ Posted: {self._format_time_ago(comment['created_utc'])}
{fit_emoji} Product Fit: {product_fit}

{type_info[0]} **Opportunity:** {type_info[1]}

"""
        
        # Add reply candidates
        if reply_candidates:
            message += "📋 **Reply Candidates (Copy & Paste Ready):**\n\n"
            
            for i, candidate in enumerate(reply_candidates, 1):
                style = candidate.get('style', f'Option {i}')
                tone = candidate.get('tone', '')
                draft = candidate.get('draft', '')
                why = candidate.get('why', '')
                
                message += f"**【{i}】{style}** ({tone})\n"
                message += f"💭 *Why this: {why}*\n"
                message += f"```\n{draft}\n```\n\n"
        
        # Add link
        message += f"🔗 [Go to Comment]({comment['url']})"
        
        return message
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as time ago string
        
        Args:
            dt: Datetime object
            
        Returns:
            Time ago string (e.g., "3 hours ago", "2 days ago")
        """
        now = datetime.now()
        diff = now - dt
        
        hours = diff.total_seconds() / 3600
        
        if hours < 1:
            mins = int(diff.total_seconds() / 60)
            return f"{mins} min{'s' if mins != 1 else ''} ago"
        elif hours < 24:
            hrs = int(hours)
            return f"{hrs} hour{'s' if hrs != 1 else ''} ago"
        else:
            days = int(hours / 24)
            return f"{days} day{'s' if days != 1 else ''} ago"
    
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
