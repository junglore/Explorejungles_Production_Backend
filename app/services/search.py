"""
Advanced search service with full-text search capabilities
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, text
from sqlalchemy.orm import selectinload
from app.models.content import Content
from app.models.media import Media
from app.models.category import Category
from app.core.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger()

class SearchService:
    """Advanced search service"""
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
    
    def preprocess_query(self, query: str) -> List[str]:
        """Preprocess search query"""
        # Convert to lowercase and remove special characters
        query = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Split into words and remove stop words
        words = [
            word.strip() for word in query.split()
            if word.strip() and len(word.strip()) > 2 and word.strip() not in self.stop_words
        ]
        
        return words
    
    async def search_content(
        self,
        db: AsyncSession,
        query: str,
        category_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search content with advanced filtering"""
        
        # Check cache first
        cache_key = f"{CacheKeys.CONTENT_LIST}:search:{hash(query + str(category_id) + str(content_type) + str(limit) + str(offset))}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Preprocess query
            search_terms = self.preprocess_query(query)
            
            if not search_terms:
                return {
                    'results': [],
                    'total': 0,
                    'query': query,
                    'suggestions': []
                }
            
            # Build base query
            base_query = select(Content).where(Content.status == 'PUBLISHED')
            
            # Add search conditions
            search_conditions = []
            for term in search_terms:
                term_pattern = f"%{term}%"
                search_conditions.append(
                    or_(
                        Content.title.ilike(term_pattern),
                        Content.content.ilike(term_pattern),
                        Content.excerpt.ilike(term_pattern),
                        Content.meta_description.ilike(term_pattern)
                    )
                )
            
            if search_conditions:
                base_query = base_query.where(and_(*search_conditions))
            
            # Add filters
            if category_id:
                base_query = base_query.where(Content.category_id == category_id)
            
            if content_type:
                base_query = base_query.where(Content.type == content_type)
            
            # Get total count
            count_query = select(func.count(Content.id)).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Get results with pagination
            results_query = (
                base_query
                .options(selectinload(Content.category))
                .order_by(
                    # Prioritize exact matches in title
                    func.case(
                        (Content.title.ilike(f"%{query}%"), 1),
                        else_=2
                    ),
                    Content.view_count.desc(),
                    Content.created_at.desc()
                )
                .offset(offset)
                .limit(limit)
            )
            
            results = await db.execute(results_query)
            content_items = results.scalars().all()
            
            # Format results
            formatted_results = []
            for content in content_items:
                # Calculate relevance score
                relevance_score = self._calculate_relevance(content, search_terms)
                
                # Generate snippet
                snippet = self._generate_snippet(content.content or content.excerpt or "", search_terms)
                
                formatted_results.append({
                    'id': str(content.id),
                    'title': content.title,
                    'excerpt': content.excerpt,
                    'snippet': snippet,
                    'type': content.type,
                    'slug': content.slug,
                    'featured_image': content.featured_image,
                    'category': {
                        'id': str(content.category.id) if content.category else None,
                        'name': content.category.name if content.category else None,
                        'slug': content.category.slug if content.category else None
                    } if content.category else None,
                    'author_name': content.author_name,
                    'published_at': content.published_at.isoformat() if content.published_at else None,
                    'view_count': content.view_count,
                    'relevance_score': relevance_score
                })
            
            # Sort by relevance score
            formatted_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Generate search suggestions
            suggestions = await self._generate_suggestions(db, query, search_terms)
            
            result = {
                'results': formatted_results,
                'total': total,
                'query': query,
                'processed_terms': search_terms,
                'suggestions': suggestions,
                'has_more': (offset + limit) < total
            }
            
            # Cache result for 5 minutes
            await cache_manager.set(cache_key, result, ttl=300)
            
            return result
            
        except Exception as e:
            logger.error(f"Content search failed: {e}")
            return {
                'results': [],
                'total': 0,
                'query': query,
                'error': str(e)
            }
    
    async def search_media(
        self,
        db: AsyncSession,
        query: str,
        media_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search media files"""
        
        try:
            search_terms = self.preprocess_query(query)
            
            if not search_terms:
                return {'results': [], 'total': 0, 'query': query}
            
            # Build search query
            base_query = select(Media)
            
            search_conditions = []
            for term in search_terms:
                term_pattern = f"%{term}%"
                search_conditions.append(
                    or_(
                        Media.title.ilike(term_pattern),
                        Media.description.ilike(term_pattern),
                        Media.photographer.ilike(term_pattern),
                        Media.national_park.ilike(term_pattern)
                    )
                )
            
            if search_conditions:
                base_query = base_query.where(and_(*search_conditions))
            
            if media_type:
                base_query = base_query.where(Media.media_type == media_type)
            
            # Get total count
            count_query = select(func.count(Media.id)).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Get results
            results_query = (
                base_query
                .order_by(Media.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            
            results = await db.execute(results_query)
            media_items = results.scalars().all()
            
            formatted_results = []
            for media in media_items:
                formatted_results.append({
                    'id': str(media.id),
                    'title': media.title,
                    'description': media.description,
                    'media_type': media.media_type,
                    'file_url': media.file_url,
                    'thumbnail_url': media.thumbnail_url,
                    'photographer': media.photographer,
                    'national_park': media.national_park,
                    'created_at': media.created_at.isoformat()
                })
            
            return {
                'results': formatted_results,
                'total': total,
                'query': query,
                'has_more': (offset + limit) < total
            }
            
        except Exception as e:
            logger.error(f"Media search failed: {e}")
            return {'results': [], 'total': 0, 'query': query, 'error': str(e)}
    
    def _calculate_relevance(self, content: Content, search_terms: List[str]) -> float:
        """Calculate relevance score for content"""
        score = 0.0
        
        title_lower = (content.title or "").lower()
        content_lower = (content.content or "").lower()
        excerpt_lower = (content.excerpt or "").lower()
        
        for term in search_terms:
            # Title matches (highest weight)
            if term in title_lower:
                score += 10.0
                if title_lower.startswith(term):
                    score += 5.0  # Bonus for starting with term
            
            # Content matches
            content_matches = content_lower.count(term)
            score += content_matches * 2.0
            
            # Excerpt matches
            if term in excerpt_lower:
                score += 3.0
        
        # Boost for popular content
        score += (content.view_count or 0) * 0.01
        
        # Boost for featured content
        if content.featured:
            score += 5.0
        
        return score
    
    def _generate_snippet(self, text: str, search_terms: List[str], max_length: int = 200) -> str:
        """Generate search result snippet with highlighted terms"""
        if not text or not search_terms:
            return text[:max_length] + "..." if len(text) > max_length else text
        
        text_lower = text.lower()
        
        # Find the best position to start the snippet
        best_pos = 0
        max_matches = 0
        
        for i in range(0, len(text) - max_length, 20):
            snippet = text_lower[i:i + max_length]
            matches = sum(1 for term in search_terms if term in snippet)
            if matches > max_matches:
                max_matches = matches
                best_pos = i
        
        # Extract snippet
        snippet = text[best_pos:best_pos + max_length]
        
        # Add ellipsis if needed
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    async def _generate_suggestions(
        self,
        db: AsyncSession,
        original_query: str,
        search_terms: List[str]
    ) -> List[str]:
        """Generate search suggestions"""
        suggestions = []
        
        try:
            # Get popular search terms from content titles
            popular_terms_query = select(Content.title).where(
                Content.status == 'PUBLISHED'
            ).order_by(Content.view_count.desc()).limit(100)
            
            result = await db.execute(popular_terms_query)
            titles = [row[0] for row in result.fetchall() if row[0]]
            
            # Extract common words from popular titles
            all_words = []
            for title in titles:
                words = self.preprocess_query(title)
                all_words.extend(words)
            
            # Find words similar to search terms
            for term in search_terms:
                similar_words = [
                    word for word in set(all_words)
                    if word != term and (
                        word.startswith(term) or
                        term in word or
                        self._levenshtein_distance(term, word) <= 2
                    )
                ]
                suggestions.extend(similar_words[:3])
            
            return list(set(suggestions))[:5]
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

# Global search service instance
search_service = SearchService()