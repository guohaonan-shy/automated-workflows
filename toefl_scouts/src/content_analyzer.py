"""Content analysis module using Google Gemini API"""

from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyzer for Reddit posts and comments using Gemini"""
    
    def __init__(
        self, 
        api_key: str,
        model: str = 'gemini-3-flash-preview',
        max_tokens: int = 2048,
        temperature: float = 1.0
    ):
        """Initialize Gemini API
        
        Args:
            api_key: Google Gemini API key
            model: Model name
            max_tokens: Maximum tokens for response
            temperature: Generation temperature (default 1.0 recommended for Gemini 3)
        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        logger.info(f"Gemini API initialized with model {model}")
    
    # ========== Post Analysis ==========
    
    def analyze_posts_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze a batch of posts
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            List of analyzed posts with scores and suggestions
        """
        analyzed_posts = []
        
        for post in posts:
            try:
                analysis = self._analyze_single_post(post)
                
                if analysis and analysis.get('score', 0) >= 5.0:
                    post_with_analysis = {**post, **analysis}
                    analyzed_posts.append(post_with_analysis)
                    logger.debug(f"Post {post['id']} scored {analysis.get('score', 0)}")
                    
            except Exception as e:
                logger.error(f"Error analyzing post {post['id']}: {e}")
        
        logger.info(f"Analyzed {len(analyzed_posts)}/{len(posts)} posts successfully")
        return analyzed_posts
    
    def _analyze_single_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a single post
        
        Args:
            post: Post dictionary
            
        Returns:
            Analysis dictionary with score and suggestions
        """
        prompt = self._build_post_analysis_prompt(post)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                ),
            )
            result = self._parse_analysis_response(response.text)
            return result
            
        except Exception as e:
            logger.error(f"Gemini API error for post {post['id']}: {e}")
            return None
    
    def _build_post_analysis_prompt(self, post: Dict[str, Any]) -> str:
        """Build prompt for post analysis
        
        Args:
            post: Post dictionary
            
        Returns:
            Prompt string
        """
        # Calculate time since posted
        time_since = datetime.now() - post['created_utc']
        hours_ago = time_since.total_seconds() / 3600
        
        prompt = f"""Analyze this TOEFL-related Reddit post for reply opportunity:

**Post Title:** {post['title']}
**Subreddit:** r/{post['subreddit']}
**Content:** {post['selftext'][:500]}
**Upvotes:** {post['score']}
**Comments:** {post['num_comments']}
**Posted:** {hours_ago:.1f} hours ago

Your task:
1. Determine if this is a genuine help-seeking post (not spam/meme/off-topic)
2. Identify the TOEFL topic (Reading/Listening/Speaking/Writing/General)
3. Evaluate reply opportunity value (1-10 score)
4. Generate 2-3 reply candidates with different approaches

Scoring criteria:
- Post quality: Is it specific, clear, and detailed? (0-3 points)
- Engagement potential: Good upvote/comment ratio? (0-2 points)
- Recency: Fresh post = better visibility (0-2 points)
- TOEFLAIR product fit: Can we naturally mention our product? (0-3 points)

Return ONLY valid JSON in this exact format:
{{
  "is_help_seeking": true/false,
  "topic": "Reading/Listening/Speaking/Writing/General",
  "score": 8.5,
  "product_fit": "high/medium/low",
  "reply_candidates": [
    {{
      "style": "Expert Mentor",
      "tone": "professional",
      "draft": "Full reply draft in English (100-200 words, ready to copy-paste)",
      "why": "Shows expertise, builds credibility"
    }},
    {{
      "style": "Friendly Peer", 
      "tone": "casual",
      "draft": "Full reply draft in English (100-200 words, ready to copy-paste)",
      "why": "Relatable, builds rapport"
    }},
    {{
      "style": "Practical Helper",
      "tone": "direct",
      "draft": "Full reply draft in English (100-200 words, ready to copy-paste)",
      "why": "Straight to the point, saves time"
    }}
  ],
  "reason": "brief explanation of score"
}}

Important: 
- ALL output must be in English (Reddit audience)
- Each draft should be ready to copy-paste
- Naturally mention TOEFLAIR where appropriate
- Keep drafts 100-200 words each"""
        
        return prompt
    
    # ========== Comment Analysis ==========
    
    def analyze_comments_batch(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze a batch of comments
        
        Args:
            comments: List of comment dictionaries
            
        Returns:
            List of analyzed comments with scores and suggestions
        """
        analyzed_comments = []
        
        for comment in comments:
            try:
                analysis = self._analyze_single_comment(comment)
                
                if analysis and analysis.get('score', 0) >= 5.0:
                    comment_with_analysis = {**comment, **analysis}
                    analyzed_comments.append(comment_with_analysis)
                    logger.debug(f"Comment {comment['id']} scored {analysis.get('score', 0)}")
                    
            except Exception as e:
                logger.error(f"Error analyzing comment {comment['id']}: {e}")
        
        logger.info(f"Analyzed {len(analyzed_comments)}/{len(comments)} comments successfully")
        return analyzed_comments
    
    def _analyze_single_comment(self, comment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a single comment
        
        Args:
            comment: Comment dictionary
            
        Returns:
            Analysis dictionary with score and suggestions
        """
        prompt = self._build_comment_analysis_prompt(comment)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                ),
            )
            result = self._parse_analysis_response(response.text)
            return result
            
        except Exception as e:
            logger.error(f"Gemini API error for comment {comment['id']}: {e}")
            return None
    
    def _build_comment_analysis_prompt(self, comment: Dict[str, Any]) -> str:
        """Build prompt for comment analysis
        
        Args:
            comment: Comment dictionary
            
        Returns:
            Prompt string
        """
        # Calculate time since posted
        time_since = datetime.now() - comment['created_utc']
        hours_ago = time_since.total_seconds() / 3600
        
        prompt = f"""Analyze this TOEFL-related Reddit comment for reply opportunity:

**Original Post:** {comment['post_title']}
**Comment by:** u/{comment['author']}
**Comment:** {comment['body'][:500]}
**Upvotes:** {comment['score']}
**Depth:** {comment['depth']} (0 = top-level)
**Posted:** {hours_ago:.1f} hours ago

Your task:
1. Evaluate the comment quality (is it helpful, accurate, complete?)
2. Identify reply opportunities (gaps, misconceptions, additions)
3. Score the opportunity value (1-10)
4. Generate 2-3 reply candidates with different approaches

Scoring criteria:
- Comment quality gap: Incomplete/inaccurate advice? (0-3 points)
- Engagement: High upvotes = more visibility (0-2 points)
- Recency: Fresh comment = better timing (0-2 points)
- Value-add potential: Can we provide unique insights? (0-3 points)

Return ONLY valid JSON in this exact format:
{{
  "is_valuable_comment": true/false,
  "opportunity_type": "supplement/correct/alternative/disagree",
  "score": 7.8,
  "product_fit": "high/medium/low",
  "reply_candidates": [
    {{
      "style": "Agree & Expand",
      "tone": "agreeable",
      "draft": "Full reply draft in English (80-150 words, ready to copy-paste)",
      "why": "Non-confrontational, adds value without stepping on toes"
    }},
    {{
      "style": "Personal Experience",
      "tone": "personal",
      "draft": "Full reply draft in English (80-150 words, ready to copy-paste)",
      "why": "Builds credibility through personal story"
    }},
    {{
      "style": "Resource Sharer",
      "tone": "helpful",
      "draft": "Full reply draft in English (80-150 words, ready to copy-paste)",
      "why": "Provides immediate practical value"
    }}
  ],
  "reason": "brief explanation of score and opportunity"
}}

Important:
- ALL output must be in English (Reddit audience)
- Each draft should be ready to copy-paste
- Reference the original comment naturally
- Mention TOEFLAIR where appropriate
- Keep drafts 80-150 words each"""
        
        return prompt
    
    # ========== Ranking ==========
    
    def rank_post_opportunities(
        self, 
        analyzed_posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank posts by opportunity score
        
        Args:
            analyzed_posts: List of analyzed posts
            
        Returns:
            Sorted list of posts (highest score first)
        """
        return sorted(
            analyzed_posts,
            key=lambda x: x.get('score', 0),
            reverse=True
        )
    
    def rank_comment_opportunities(
        self, 
        analyzed_comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank comments by opportunity score
        
        Args:
            analyzed_comments: List of analyzed comments
            
        Returns:
            Sorted list of comments (highest score first)
        """
        return sorted(
            analyzed_comments,
            key=lambda x: x.get('score', 0),
            reverse=True
        )
    
    # ========== Helper Methods ==========
    
    def _parse_analysis_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Gemini response into structured data
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Extract JSON from markdown code blocks if present
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            elif '```' in response_text:
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            
            # Parse JSON
            result = json.loads(response_text)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            return None
