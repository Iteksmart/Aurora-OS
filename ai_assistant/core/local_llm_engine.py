"""
Aurora OS - Local LLM Engine
Core AI engine embedded directly into the OS for offline AI capabilities
Supports Llama 3.2 and other open-source models
"""

import os
import sys
import json
import logging
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path

# Optional dependencies - graceful fallback
try:
    import torch
    import numpy as np
    from transformers import (
        AutoTokenizer, 
        AutoModelForCausalLM, 
        pipeline,
        TextIteratorStreamer,
        GenerationConfig
    )
    TORCH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"PyTorch/Transformers not available: {e}")
    logging.info("AI features will be disabled. Install with: pip install torch transformers")
    TORCH_AVAILABLE = False
    torch = None
    np = None

from concurrent.futures import ThreadPoolExecutor
import gc

@dataclass
class AIRequest:
    """AI request structure"""
    prompt: str
    context: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False
    system_prompt: Optional[str] = None

@dataclass
class AIResponse:
    """AI response structure"""
    text: str
    tokens_used: int
    confidence: float
    context_used: bool
    response_time: float

class LocalLLMEngine:
    """
    Local LLM engine for Aurora OS
    Embeds AI capabilities directly into the OS
    """
    
    def __init__(self, model_path: str = "/opt/aurora/models/llama-3.2-3b"):
        self.model_path = Path(model_path)
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._detect_device()
        self.context_memory = []
        self.system_context = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.is_loaded = False
        self.model_loaded_event = threading.Event()
        self.torch_available = TORCH_AVAILABLE
        
        # Aurora OS specific system prompts
        self.system_prompts = {
            "assistant": "You are Aurora, the AI assistant embedded in Aurora OS. You help users manage their system, complete tasks, and optimize their experience. Be helpful, efficient, and proactive.",
            "system_admin": "You are Aurora's system administration AI. You help manage system settings, troubleshoot issues, and optimize performance. Focus on technical accuracy and system stability.",
            "task_executor": "You are Aurora's task execution AI. You break down complex tasks into actionable steps and help users accomplish their goals efficiently.",
            "life_optimizer": "You are Aurora's life optimization AI. You help users optimize their digital life, manage time, and achieve their goals across work, health, and personal growth."
        }
        
        self.logger = logging.getLogger("Aurora.LocalLLM")
        self._setup_logging()
        
        # Check if dependencies are available
        if not self.torch_available:
            self.logger.warning("PyTorch not available - AI features disabled")
            self.logger.info("To enable AI features, install: pip install torch transformers")
        
    def _setup_logging(self):
        """Setup logging for the LLM engine"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "local_llm.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
    def _detect_device(self) -> str:
        """Detect optimal device for model inference"""
        if not self.torch_available:
            return "none"
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    async def initialize_model(self):
        """Initialize the LLM model asynchronously"""
        if not self.torch_available:
            self.logger.warning("Cannot initialize model - PyTorch not available")
            return False
            
        try:
            self.logger.info(f"Loading model from {self.model_path} on {self.device}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                local_files_only=True
            )
            
            # Add pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with optimal settings
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                local_files_only=True,
                low_cpu_mem_usage=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            # Create generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            self.is_loaded = True
            self.model_loaded_event.set()
            self.logger.info("Model loaded successfully")
            
            # Initialize system context
            await self._initialize_system_context()
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            # Fallback to smaller model or cloud service
            await self._fallback_model()
    
    async def _initialize_system_context(self):
        """Initialize system context for AI awareness"""
        self.system_context = {
            "os_version": "Aurora OS 1.0.0",
            "kernel_version": os.uname().release,
            "hardware_info": await self._get_hardware_info(),
            "installed_apps": await self._get_installed_apps(),
            "user_preferences": await self._load_user_preferences(),
            "system_resources": await self._get_system_resources()
        }
    
    async def _get_hardware_info(self) -> Dict:
        """Get hardware information"""
        try:
            import psutil
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').total,
                "gpu_info": self._detect_gpu()
            }
        except:
            return {"cpu_count": 4, "memory_total": 8589934592}
    
    def _detect_gpu(self) -> List[str]:
        """Detect available GPUs"""
        gpus = []
        if self.torch_available and torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                gpus.append(torch.cuda.get_device_name(i))
        return gpus
    
    async def _get_installed_apps(self) -> List[str]:
        """Get list of installed applications"""
        apps = []
        try:
            # Scan common application directories
            app_dirs = ['/usr/share/applications', '/var/lib/flatpak/exports/share/applications']
            for app_dir in app_dirs:
                if os.path.exists(app_dir):
                    for file in os.listdir(app_dir):
                        if file.endswith('.desktop'):
                            apps.append(file.replace('.desktop', ''))
        except Exception as e:
            self.logger.warning(f"Could not get installed apps: {e}")
        return apps[:20]  # Limit to first 20 apps
    
    async def _load_user_preferences(self) -> Dict:
        """Load user preferences"""
        prefs_file = Path.home() / ".config" / "aurora" / "preferences.json"
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"theme": "aurora", "voice_enabled": True}
    
    async def _get_system_resources(self) -> Dict:
        """Get current system resource usage"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "battery_percent": psutil.sensors_battery().percent if psutil.sensors_battery() else None
            }
        except:
            return {"cpu_percent": 0, "memory_percent": 50, "disk_percent": 30}
    
    async def _fallback_model(self):
        """Fallback model implementation"""
        self.logger.warning("Using fallback response system")
        self.fallback_mode = True
    
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response for user request"""
        if not self.is_loaded:
            await self._wait_for_model()
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Build prompt with system context
            full_prompt = self._build_prompt(request)
            
            # Generate response
            if request.stream:
                return await self._generate_streaming(request, full_prompt, start_time)
            else:
                return await self._generate_regular(request, full_prompt, start_time)
                
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return AIResponse(
                text="I'm having trouble processing your request right now. Please try again.",
                tokens_used=0,
                confidence=0.0,
                context_used=False,
                response_time=asyncio.get_event_loop().time() - start_time
            )
    
    def _build_prompt(self, request: AIRequest) -> str:
        """Build complete prompt with system context"""
        prompt_parts = []
        
        # System prompt
        system_prompt = request.system_prompt or self.system_prompts["assistant"]
        prompt_parts.append(f"System: {system_prompt}")
        
        # Add system context if relevant
        if request.context and "system" in request.context.lower():
            context_str = self._format_system_context()
            prompt_parts.append(f"System Context: {context_str}")
        
        # User context if provided
        if request.context:
            prompt_parts.append(f"Context: {request.context}")
        
        # User prompt
        prompt_parts.append(f"User: {request.prompt}")
        prompt_parts.append("Assistant: ")
        
        return "\n\n".join(prompt_parts)
    
    def _format_system_context(self) -> str:
        """Format system context for prompt"""
        context_items = []
        if self.system_context.get("system_resources"):
            resources = self.system_context["system_resources"]
            context_items.append(f"CPU: {resources.get('cpu_percent', 0)}%")
            context_items.append(f"Memory: {resources.get('memory_percent', 0)}%")
        
        if self.system_context.get("installed_apps"):
            apps = self.system_context["installed_apps"][:5]
            context_items.append(f"Installed apps: {', '.join(apps)}")
        
        return ", ".join(context_items)
    
    async def _generate_regular(self, request: AIRequest, prompt: str, start_time: float) -> AIResponse:
        """Generate regular (non-streaming) response"""
        if not self.torch_available:
            return AIResponse(
                text="AI features require PyTorch to be installed. Please install with: pip install torch transformers",
                tokens_used=0,
                confidence=0.0,
                context_used=False,
                response_time=asyncio.get_event_loop().time() - start_time
            )
            
        generation_config = GenerationConfig(
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        
        # Generate response
        with torch.no_grad():
            outputs = self.pipeline(
                prompt,
                generation_config=generation_config,
                num_return_sequences=1,
                return_full_text=False
            )
        
        response_text = outputs[0]['generated_text'].strip()
        tokens_used = len(self.tokenizer.encode(response_text))
        
        return AIResponse(
            text=response_text,
            tokens_used=tokens_used,
            confidence=0.8,  # Placeholder - could be calculated based on generation
            context_used=bool(request.context),
            response_time=asyncio.get_event_loop().time() - start_time
        )
    
    async def _generate_streaming(self, request: AIRequest, prompt: str, start_time: float) -> AIResponse:
        """Generate streaming response"""
        if not self.torch_available:
            return AIResponse(
                text="AI features require PyTorch to be installed. Please install with: pip install torch transformers",
                tokens_used=0,
                confidence=0.0,
                context_used=False,
                response_time=asyncio.get_event_loop().time() - start_time
            )
            
        streamer = TextIteratorStreamer(
            self.tokenizer, 
            skip_prompt=True, 
            skip_special_tokens=True
        )
        
        generation_config = GenerationConfig(
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        
        # Run generation in separate thread
        def generate():
            self.pipeline(
                prompt,
                generation_config=generation_config,
                streamer=streamer,
                num_return_sequences=1,
                return_full_text=False
            )
        
        self.executor.submit(generate)
        
        # Collect streaming response
        response_text = ""
        for chunk in streamer:
            response_text += chunk
            # Could emit streaming events here
        
        tokens_used = len(self.tokenizer.encode(response_text))
        
        return AIResponse(
            text=response_text,
            tokens_used=tokens_used,
            confidence=0.8,
            context_used=bool(request.context),
            response_time=asyncio.get_event_loop().time() - start_time
        )
    
    async def _wait_for_model(self):
        """Wait for model to load"""
        if not self.is_loaded:
            await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                self.model_loaded_event.wait
            )
    
    def update_context(self, context_data: Dict[str, Any]):
        """Update system context"""
        self.system_context.update(context_data)
    
    def add_to_memory(self, interaction: Dict[str, str]):
        """Add interaction to memory for context"""
        self.context_memory.append(interaction)
        # Keep only last 50 interactions
        if len(self.context_memory) > 50:
            self.context_memory.pop(0)
    
    def get_memory_context(self) -> str:
        """Get relevant memory context"""
        if not self.context_memory:
            return ""
        
        # Return last 5 interactions as context
        recent = self.context_memory[-5:]
        context_parts = []
        for interaction in recent:
            context_parts.append(f"User: {interaction.get('user', '')}")
            context_parts.append(f"Assistant: {interaction.get('assistant', '')}")
        
        return "\n".join(context_parts)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        if self.pipeline:
            del self.pipeline
        
        gc.collect()
        if self.torch_available and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.executor.shutdown(wait=True)

# Global instance for the OS
_llm_engine = None

def get_llm_engine() -> LocalLLMEngine:
    """Get global LLM engine instance"""
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LocalLLMEngine()
    return _llm_engine

async def initialize_ai_system():
    """Initialize the AI system"""
    engine = get_llm_engine()
    await engine.initialize_model()
    return engine