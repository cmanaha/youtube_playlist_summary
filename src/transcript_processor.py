from typing import Optional, Set, Dict, Any
from collections.abc import Callable
from pydantic import BaseModel, Field
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import json
from llm_provider import LLMConfig, LLMProvider, RetryConfig

class TranscriptProcessor:
    def __init__(
        self, 
        batch_size: int = 1, 
        num_gpus: int = 0, 
        num_cpus: int = 4, 
        model: str = 'llama3.2', 
        num_threads: int = 4
    ) -> None:
        # Configure LLM settings
        llm_config = LLMConfig(
            model=model,
            num_thread=num_threads,
            num_gpu=num_gpus,
            retry=RetryConfig()  # Add retry configuration
        )
        
        # Store model name for testing
        self.model_name: str = model
        
        # Add GPU configuration if specified
        if num_gpus > 0:
            llm_config.num_gpu = num_gpus
        
        # Add CPU configuration if specified
        if num_cpus > 0:
            llm_config.num_thread = num_cpus
        
        # Create LLM instance using provider
        self.llm = LLMProvider.create_llm(llm_config)
        
        self.batch_size: int = max(1, batch_size)
        
        # Define valid categories


        self.valid_categories: Set[str] = {
            "Keynote", "Security", "GitOps", "AI & ML", "Sustainability",
            "Scaling", "Scheduling", "Performance Engineering", "Observability", 
            "Analytics", "Databases", "Operations"
            "HPC", "Developer Experience", "Compute",
            "Storage", "Networking", "Serverless","Architecture"           
        }

        self.filter_categories: Optional[Set[str]] = None
        
        # Add preselected categories storage
        self.preselected_categories: Set[str] = set()
        
        # Prompt template for categorization
        self.category_prompt = PromptTemplate(
            template="""Based on the following video title and transcript, 
            choose the most appropriate category. Please do not make the category
            too specific, it should be a broad category. 
            
            Previously used categories: {preselected_categories}
            If the content is similar to any of the previously used categories, 
            please reuse that category for better grouping.
            
            If no previous categories match, you can choose from these examples: {categories}
            
            Title: {title}
            Transcript: {transcript}
            
            Respond ONLY with a JSON object in this format:
            {{"category": "chosen_category"}}""",
            input_variables=["preselected_categories", "categories", "title", "transcript"]
        )
        
        # Prompt template for summarization
        self.summary_prompt = PromptTemplate(
            template="""Provide a concise one paragraph with 3 sentences at least. Use an abstract style as the
            one you would propose for a conference talk with the summary of this video content.
            
            Title: {title}
            Transcript: {transcript}
            
            Respond ONLY with a JSON object in this format:
            {{"summary": "your_two_sentence_summary"}}""",
            input_variables=["title", "transcript"]
        )

    def set_filter_categories(self, categories: Optional[str] = None) -> None:
        """Set categories to filter by."""
        if categories:
            # Convert comma-separated string to set of normalized categories
            self.filter_categories = {self._normalize_category(cat) for cat in categories.split(',')}
            
            # Validate categories against valid ones
            normalized_valid_categories = {self._normalize_category(cat) for cat in self.valid_categories}
            invalid_categories = self.filter_categories - normalized_valid_categories
            
            if invalid_categories:
                closest_matches = {
                    cat: self._find_closest_match(cat, self.valid_categories)
                    for cat in invalid_categories
                }
                suggestions = [
                    f"'{cat}' (did you mean '{closest}'?)"
                    for cat, closest in closest_matches.items()
                ]
                raise ValueError(f"Invalid categories found: {', '.join(suggestions)}\n"
                               f"Valid categories are: {', '.join(sorted(self.valid_categories))}")
        else:
            self.filter_categories = None

    def _normalize_category(self, category: str, /) -> str:
        """Normalize category string for comparison."""
        return category.strip().lower()

    def _find_closest_match(self, category: str, valid_categories: Set[str]) -> str:
        """Find the closest matching valid category."""
        normalized_category = self._normalize_category(category)
        normalized_valid = {self._normalize_category(cat): cat for cat in valid_categories}
        
        # First try exact match after normalization
        if normalized_category in normalized_valid:
            return normalized_valid[normalized_category]
        
        # Then try partial matches
        for valid_norm, valid_orig in normalized_valid.items():
            if normalized_category in valid_norm or valid_norm in normalized_category:
                return valid_orig
        
        # Finally return the first valid category as fallback
        return next(iter(valid_categories))

    def matches_filter(self, category: str, /) -> bool:
        """Check if a category matches the filter criteria."""
        if not self.filter_categories:
            return True  # No filter means all categories match
        return self._normalize_category(category) in self.filter_categories

    def _get_category(self, title: str, transcript: str) -> str:
        """Get category for the video."""
        try:
            # Format preselected categories for the prompt
            preselected_cats = ", ".join(sorted(self.preselected_categories)) if self.preselected_categories else "Uncategorized"
            
            # Invoke LLM for categorization
            response = self.llm.invoke(
                self.category_prompt.format(
                    preselected_categories=preselected_cats,
                    categories=", ".join(sorted(self.valid_categories)),
                    title=title,
                    transcript=transcript
                )
            )
            
            # Parse response
            result = json.loads(response)
            category = result.get("category", "Uncategorized")
            
            # Try to match with valid categories
            if category != "Uncategorized":
                normalized_category = self._normalize_category(category)
                for valid_category in self.valid_categories:
                    if self._normalize_category(valid_category) == normalized_category:
                        # Add to preselected categories for future use
                        self.preselected_categories.add(valid_category)
                        return valid_category
            
            return category
        except Exception as e:
            print(f"Error getting category: {str(e)}")
            return "Uncategorized"

    def _get_summary(self, title: str, transcript: str) -> str:
        """Get summary for the video."""
        try:
            # Invoke LLM for summarization
            response = self.llm.invoke(
                self.summary_prompt.format(
                    title=title,
                    transcript=transcript
                )
            )
            
            # Parse response
            result = json.loads(response)
            return result.get("summary", "Failed to generate summary.")
        except Exception as e:
            print(f"Error getting summary: {str(e)}")
            return "Failed to generate summary."

    def get_category(self, title: str, transcript: str) -> str:
        """Get category for the video."""
        try:
            category = self._get_category(title, transcript)
            return category
        except Exception as e:
            print(f"Error getting category: {str(e)}")
            return "Uncategorized"

    def get_summary(self, title: str, transcript: str) -> str:
        """Get summary for the video."""
        try:
            summary = self._get_summary(title, transcript)
            return summary
        except Exception as e:
            print(f"Error getting summary: {str(e)}")
            return "Failed to generate summary."

    def process_video(self, title: str, transcript: str) -> Optional[Dict[str, str]]:
        """Categorize and summarize the video."""
        try:
            category = self.get_category(title, transcript)
            summary = self.get_summary(title, transcript)
            
            # If either call returned default values due to errors, return None
            if category == "Uncategorized" or summary == "Failed to generate summary.":
                return None
            
            return {
                "category": category,
                "summary": summary
            }
        except Exception as e:
            print(f"Error in categorize_video: {str(e)}")
            return None 