from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from langchain_ollama import OllamaLLM
import boto3
from pydantic import BaseModel, Field
import time
from rich.console import Console
import random
import json

console = Console()

class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_retries: int = Field(default=5)
    initial_delay: float = Field(default=1.0)
    max_delay: float = Field(default=32.0)
    exponential_base: float = Field(default=2.0)
    jitter: float = Field(default=0.1)

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
    
    def invoke(self, prompt: str) -> str:
        """Invoke with exponential backoff retry logic."""
        delay = self.retry_config.initial_delay
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries):
            try:
                return self._raw_invoke(prompt)
            except Exception as e:
                last_exception = e
                if attempt == self.retry_config.max_retries - 1:
                    # Last attempt, provide detailed error
                    console.log(f"[red]All retry attempts failed. Last error: {str(e)}[/red]")
                    raise
                
                # Calculate delay with jitter
                jitter = random.uniform(
                    -self.retry_config.jitter * delay,
                    self.retry_config.jitter * delay
                )
                current_delay = min(
                    delay + jitter,
                    self.retry_config.max_delay
                )
                
                console.log(
                    f"[yellow]Attempt {attempt + 1} failed: {str(e)}. "
                    f"Retrying in {current_delay:.2f} seconds...[/yellow]"
                )
                
                time.sleep(current_delay)
                delay *= self.retry_config.exponential_base
        
        # This should never happen due to the raise in the loop
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
    INFERENCE_PROFILE_NAME = "YoutubePlaylistAnalyzer-123120241249"
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = boto3.client('bedrock-runtime')
        self.bedrock = boto3.client('bedrock')
        self.model_id = self._get_bedrock_model_id(config.model)
        self.temperature = config.temperature
        self.max_tokens = config.num_ctx
        self.region = self.client.meta.region_name
        
        # Setup Nova inference profile if needed
        self.inference_profile_id = None
        if 'nova' in self.model_id:
            self._setup_nova_profile()
    
    def _find_nova_profile(self) -> Optional[str]:
        """Find an existing Nova inference profile."""
        try:
            paginator = self.bedrock.get_paginator('list_inference_profiles')
            app_profiles = paginator.paginate(typeEquals='APPLICATION')
            
            for page in app_profiles:
                for profile in page['inferenceProfileSummaries']:
                    if (profile['inferenceProfileName'] == self.INFERENCE_PROFILE_NAME and
                        any('nova' in model['modelArn'].lower() for model in profile['models'])):
                        console.log(f"[green]Found existing Nova inference profile: {profile['inferenceProfileId']}[/green]")
                        return profile['inferenceProfileId']
            
            return None
            
        except Exception as e:
            console.log(f"[yellow]Error finding Nova profile: {str(e)}[/yellow]")
            return None
    
    def _setup_nova_profile(self) -> None:
        """Setup or find Nova inference profile."""
        try:
            # Try to find existing profile
            profile_id = self._find_nova_profile()
            if profile_id:
                self.inference_profile_id = profile_id
                return
            
            # Create new profile if none exists
            console.log(f"[yellow]Creating new Nova inference profile: {self.INFERENCE_PROFILE_NAME}[/yellow]")
            response = self.bedrock.create_inference_profile(
                inferenceProfileName=self.INFERENCE_PROFILE_NAME,
                description="Inference profile for Nova Lite model",
                modelSource={
                    'copyFrom': f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-lite-v1:0"
                },
                tags=[{
                    "key": "AppName",
                    "value": "YoutubePlaylistSummarizer"
                }]
            )
            
            self.inference_profile_id = response['inferenceProfile']['inferenceProfileId']
            console.log(f"[green]Successfully created Nova inference profile: {self.inference_profile_id}[/green]")
            
        except Exception as e:
            console.log(f"[red]Error setting up Nova profile: {str(e)}[/red]")
            # Continue without profile
            self.inference_profile_id = None
    
    def _invoke_nova(self, prompt: str) -> str:
        """Invoke Nova model using direct Bedrock API."""
        request_body = {
            "prompt": prompt,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        try:
            # Try to use inference profile if available
            if self.inference_profile_id:
                try:
                    response = self.client.invoke_model(
                        modelId=self.inference_profile_id,
                        body=json.dumps(request_body)
                    )
                    response_body = json.loads(response['body'].read())
                    return response_body['completion']
                except Exception as profile_error:
                    console.log(f"[yellow]Error using inference profile: {str(profile_error)}. Falling back to direct invocation.[/yellow]")
            
        except Exception as e:
            console.log(f"[red]Error invoking Nova: {str(e)}[/red]")
            raise
    
    def _get_bedrock_model_id(self, model: str) -> str:
        """Map friendly model names to Bedrock model IDs."""
        model_map = {
            "claude": "anthropic.claude-3-sonnet-20240229-v1:0",
            "claude-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
            "nova": "amazon.nova-lite-v1:0",
        }
        model_id = model_map.get(model, model)
        if not model_id:
            raise ValueError(f"Unknown model: {model}")
        return model_id
    
    def _format_claude_prompt(self, prompt: str) -> str:
        """Format prompt for Claude models."""
        return f"\n\nHuman: {prompt}\n\nAssistant: "
    
    def _invoke_claude(self, prompt: str) -> str:
        """Invoke Claude model using direct Bedrock API."""
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
            return response_body['content'][0]['text']
        except Exception as e:
            console.log(f"[red]Error invoking Claude: {str(e)}[/red]")
            raise
    
    def _raw_invoke(self, prompt: str) -> str:
        """Raw invocation using appropriate model-specific method."""
        try:
            if 'claude' in self.model_id:
                return self._invoke_claude(prompt)
            elif 'nova' in self.model_id:
                return self._invoke_nova(prompt)
            else:
                raise ValueError(f"Unsupported model: {self.model_id}")
        except Exception as e:
            console.log(f"[red]Error invoking Bedrock model: {str(e)}[/red]")
            raise

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