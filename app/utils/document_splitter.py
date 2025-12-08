"""Document splitting utilities for credit agreements.

This module provides intelligent splitting strategies for long credit agreement
documents, focusing on splitting by Articles (Article I, Article II, etc.)
which is the standard structure for legal credit agreements.
"""

import re
import logging
from typing import List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    text: str
    article_number: int | None
    article_title: str | None
    chunk_index: int
    start_char: int
    end_char: int


class CreditAgreementSplitter:
    """Splits credit agreement documents into logical sections.
    
    Uses Article-based splitting (Article I: Definitions, Article II: The Credits, etc.)
    which is the standard structure for syndicated credit agreements.
    """
    
    # Pattern to match Article headers (e.g., "ARTICLE I", "Article II", "ARTICLE 3")
    ARTICLE_PATTERN = re.compile(
        r'ARTICLE\s+([IVX]+|\d+)[\s:\.]+(.+?)(?=\n|$)',
        re.IGNORECASE | re.MULTILINE
    )
    
    def __init__(self, min_chunk_size: int = 500, max_chunk_size: int = 8000):
        """Initialize the splitter.
        
        Args:
            min_chunk_size: Minimum characters per chunk (default: 500)
            max_chunk_size: Maximum characters per chunk (default: 8000, fits in context)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def split_by_articles(self, text: str) -> List[DocumentChunk]:
        """Split document by Article sections.
        
        Args:
            text: The full document text.
            
        Returns:
            List of DocumentChunk objects, each representing an Article section.
        """
        chunks: List[DocumentChunk] = []
        
        # Find all Article headers
        article_matches = list(self.ARTICLE_PATTERN.finditer(text))
        
        if not article_matches:
            # No articles found, split by paragraphs or return as single chunk
            logger.warning("No Article sections found, returning document as single chunk")
            return [DocumentChunk(
                text=text[:self.max_chunk_size],
                article_number=None,
                article_title=None,
                chunk_index=0,
                start_char=0,
                end_char=min(len(text), self.max_chunk_size)
            )]
        
        # Process each Article section
        for idx, match in enumerate(article_matches):
            article_num_str = match.group(1)
            article_title = match.group(2).strip()
            
            # Determine start and end positions
            start_pos = match.start()
            
            # End position is either the start of the next article, or end of document
            if idx + 1 < len(article_matches):
                end_pos = article_matches[idx + 1].start()
            else:
                end_pos = len(text)
            
            # Extract the article text
            article_text = text[start_pos:end_pos].strip()
            
            # If article is too long, split it further
            if len(article_text) > self.max_chunk_size:
                sub_chunks = self._split_large_article(
                    article_text,
                    article_num_str,
                    article_title,
                    start_pos
                )
                chunks.extend(sub_chunks)
            else:
                # Convert article number (Roman or Arabic) to integer for sorting
                article_number = self._parse_article_number(article_num_str)
                
                chunks.append(DocumentChunk(
                    text=article_text,
                    article_number=article_number,
                    article_title=article_title,
                    chunk_index=len(chunks),
                    start_char=start_pos,
                    end_char=end_pos
                ))
        
        return chunks
    
    def _split_large_article(
        self,
        article_text: str,
        article_num_str: str,
        article_title: str,
        base_start_pos: int
    ) -> List[DocumentChunk]:
        """Split a large article into smaller chunks.
        
        Uses paragraph boundaries to maintain semantic coherence.
        """
        chunks = []
        paragraphs = article_text.split('\n\n')
        
        current_chunk = []
        current_size = 0
        chunk_start = 0
        
        article_number = self._parse_article_number(article_num_str)
        
        for para in paragraphs:
            para_size = len(para)
            
            # If adding this paragraph would exceed max size, finalize current chunk
            if current_size + para_size > self.max_chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        article_number=article_number,
                        article_title=article_title,
                        chunk_index=len(chunks),
                        start_char=base_start_pos + chunk_start,
                        end_char=base_start_pos + chunk_start + len(chunk_text)
                    ))
                    chunk_start += len(chunk_text)
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(para)
            current_size += para_size + 2  # +2 for '\n\n'
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(DocumentChunk(
                text=chunk_text,
                article_number=article_number,
                article_title=article_title,
                chunk_index=len(chunks),
                start_char=base_start_pos + chunk_start,
                end_char=base_start_pos + chunk_start + len(chunk_text)
            ))
        
        return chunks
    
    def _parse_article_number(self, article_num_str: str) -> int:
        """Parse article number from Roman numeral or Arabic numeral.
        
        Args:
            article_num_str: String like "I", "II", "3", etc.
            
        Returns:
            Integer representation of the article number.
        """
        article_num_str = article_num_str.strip().upper()
        
        # Try Roman numeral first
        roman_to_int = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
            'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15
        }
        
        if article_num_str in roman_to_int:
            return roman_to_int[article_num_str]
        
        # Try Arabic numeral
        try:
            return int(article_num_str)
        except ValueError:
            # Default to 0 if can't parse
            return 0

