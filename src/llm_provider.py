from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from langchain_community.llms import Bedrock
from langchain_ollama import OllamaLLM
import boto3
from pydantic import BaseModel

class LLMConfig(BaseModel):
    """Configuration for the LLM."""
    model: str = "llama3.2"
    temperature: float = 0.7
    format: str = "json"
    num_thread: int = 4
    num_ctx: int = 16384
    repeat_last_n: int = 2
    num_gpu: int = 0

class BaseLLM(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        pass

class OllamaWrapper(BaseLLM):
    def __init__(self, config: LLMConfig):
        # Map friendly names to Ollama model names
        model_name = self._get_ollama_model_id(config.model)
        config.model = model_name
        self.llm = OllamaLLM(**config.model_dump())
    
    def _get_ollama_model_id(self, model: str) -> str:
        """Map friendly model names to Ollama model IDs."""
        model_map = {
            "llama3.2": "llama3.2",
            "mistral": "mistral",
        }
        return model_map.get(model, model)
    
    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt)

class BedrockWrapper(BaseLLM):
    def __init__(self, config: LLMConfig):
        bedrock = boto3.client('bedrock-runtime')
        model_id = self._get_bedrock_model_id(config.model)
        self.llm = Bedrock(
            client=bedrock,
            model_id=model_id,
            model_kwargs={
                "temperature": config.temperature,
                "max_tokens": config.num_ctx
            }
        )
    
    def _get_bedrock_model_id(self, model: str) -> str:
        """Map friendly model names to Bedrock model IDs."""
        model_map = {
            "claude": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "nova": "amazon.nova-lite-v1:0",
        }
        return model_map.get(model, model)
    
    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt)

class LLMProvider:
    """Factory for creating LLM instances."""
    
    @staticmethod
    def create_llm(config: LLMConfig) -> BaseLLM:
        """Create an LLM instance based on the model name."""
        bedrock_models = {"claude", "claude-haiku", "nova"}
        ollama_models = {"llama3.2", "mistral"}
        
        if config.model in bedrock_models:
            return BedrockWrapper(config)
        elif config.model in ollama_models or config.model.startswith("llama"):
            return OllamaWrapper(config)
        else:
            # Default to Ollama for unknown models
            return OllamaWrapper(config) 