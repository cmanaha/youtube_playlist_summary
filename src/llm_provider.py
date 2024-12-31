from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from langchain_ollama import OllamaLLM
import boto3
from pydantic import BaseModel, Field
import time
from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.style import Style
import random
import json

# Create a separate console for cost logging that doesn't interfere with progress bars
cost_console = Console(stderr=True, style=Style(color="blue"))

# Claude model costs per 1K input/output tokens (as of March 2024)
BEDROCK_COSTS = {
    "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
    "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.0008, "output": 0.004},
}

class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_retries: int = Field(default=5)
    initial_delay: float = Field(default=2.0)
    max_delay: float = Field(default=60.0)
    exponential_base: float = Field(default=2.0)
    jitter: float = Field(default=0.2)

class LLMConfig(BaseModel):
    """Configuration for the LLM."""
    model: str = Field(default="llama3.2")
    temperature: float = Field(default=0.7)
    format: str = Field(default="json")
    num_thread: int = Field(default=4)
    num_ctx: int = Field(default=16384)
    repeat_last_n: int = Field(default=2)
    num_gpu: int = Field(default=0)
    retry: RetryConfig = Field(default_factory=RetryConfig)

class BaseLLM(ABC):
    def __init__(self, config: LLMConfig):
        self.retry_config = config.retry
    
    @abstractmethod
    def _raw_invoke(self, prompt: str) -> str:
        """Raw invocation without retries."""
        pass
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if the error is retryable."""
        error_str = str(error).lower()
        return any(msg in error_str for msg in [
            'throttlingexception',
            'too many tokens',
            'rate exceeded',
            'timeout',
            'connection',
            'temporarily unavailable'
        ])
    
    def invoke(self, prompt: str) -> str:
        """Invoke with exponential backoff retry logic."""
        delay = self.retry_config.initial_delay
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries):
            try:
                return self._raw_invoke(prompt)
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e) or attempt == self.retry_config.max_retries - 1:
                    cost_console.log(f"[red]Error not retryable or max retries reached. Last error: {str(e)}[/red]")
                    raise
                
                # Calculate delay with jitter
                jitter = random.uniform(
                    -self.retry_config.jitter * delay,
                    self.retry_config.jitter * delay
                )
                
                # Ensure minimum delay and respect max delay
                current_delay = min(
                    max(delay + jitter, self.retry_config.initial_delay),
                    self.retry_config.max_delay
                )
                
                cost_console.log(
                    f"[yellow]Attempt {attempt + 1} failed with throttling, "
                    f"waiting {current_delay:.2f} seconds before retry: {str(e)}[/yellow]"
                )
                
                time.sleep(current_delay)
                delay = min(delay * self.retry_config.exponential_base, self.retry_config.max_delay)
        
        raise Exception(f"Max retries exceeded. Last error: {str(last_exception)}")

class OllamaWrapper(BaseLLM):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Map friendly names to Ollama model names
        model_name = self._get_ollama_model_id(config.model)
        config_dict = config.model_dump(exclude={'retry'})
        config_dict['model'] = model_name
        self.llm = OllamaLLM(**config_dict)
    
    def _get_ollama_model_id(self, model: str) -> str:
        """Map friendly model names to Ollama model IDs."""
        model_map = {
            "llama3.2": "llama3.2",
            "mistral": "mistral",
        }
        return model_map.get(model, model)
    
    def _raw_invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt)

class BedrockWrapper(BaseLLM):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = boto3.client('bedrock-runtime')
        self.model_id = self._get_bedrock_model_id(config.model)
        self.temperature = config.temperature
        self.max_tokens = config.num_ctx
        self.total_cost = 0.0
    
    def _get_bedrock_model_id(self, model: str) -> str:
        """Map friendly model names to Bedrock model IDs."""
        model_map = {
            "claude": "anthropic.claude-3-haiku-20240307-v1:0",
            "claude-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        }

        model_id = model_map.get(model, model)
        if not model_id:
            raise ValueError(f"Unknown model: {model}")
        return model_id
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model invocation."""
        if self.model_id not in BEDROCK_COSTS:
            console.log(f"[yellow]Warning: No cost information for model {self.model_id}[/yellow]")
            return 0.0
        
        rates = BEDROCK_COSTS[self.model_id]
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]
        total_cost = input_cost + output_cost
        
        return total_cost
    
    def _raw_invoke(self, prompt: str) -> str:
        """Raw invocation using Claude models with cost tracking."""
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            response_body = json.loads(response['body'].read())
            
            # Extract token counts and calculate cost
            input_tokens = response_body.get('usage', {}).get('input_tokens', 0)
            output_tokens = response_body.get('usage', {}).get('output_tokens', 0)
            invocation_cost = self._calculate_cost(input_tokens, output_tokens)
            self.total_cost += invocation_cost
            
            # Log the cost information to stderr to avoid progress bar interference
            cost_console.log(
                f"\nBedrock invocation cost: ${invocation_cost:.4f} "
                f"(Input: {input_tokens} tokens, Output: {output_tokens} tokens) "
                f"Total Cost accumulated in this session: ${self.total_cost:.4f}"
            )
            
            return response_body['content'][0]['text']
            
        except Exception as e:
            cost_console.log(f"\n[red]Error invoking Bedrock model: {str(e)}[/red]")
            raise
    
    def get_total_cost(self) -> float:
        """Get the total cost of all invocations."""
        return self.total_cost

class LLMProvider:
    """Factory for creating LLM instances."""
    
    @staticmethod
    def create_llm(config: LLMConfig) -> BaseLLM:
        """Create an LLM instance based on the model name."""
        bedrock_models = {"claude", "claude-haiku"}
        ollama_models = {"llama3.2", "mistral"}
        
        if config.model in bedrock_models:
            return BedrockWrapper(config)
        elif config.model in ollama_models or config.model.startswith("llama"):
            return OllamaWrapper(config)
        else:
            # Default to Ollama for unknown models
            return OllamaWrapper(config) 