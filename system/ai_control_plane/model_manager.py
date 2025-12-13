#!/usr/bin/env python3
"""
AI Model Management System for Aurora OS
Handles model versioning, optimization, and dynamic loading
"""

import asyncio
import logging
import json
import hashlib
import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import shutil
import tempfile
import threading
import time
import psutil

class ModelType(Enum):
    """Types of AI models managed by the system"""
    NLP_INTENT = "nlp_intent"
    NLP_ENTITY = "nlp_entity"
    NLP_SENTIMENT = "nlp_sentiment"
    VISION_FACE = "vision_face"
    VISION_GESTURE = "vision_gesture"
    VISION_POSE = "vision_pose"
    SPEECH_RECOGNITION = "speech_recognition"
    SPEECH_EMOTION = "speech_emotion"
    RECOMMENDATION = "recommendation"
    PREDICTION = "prediction"
    ANOMALY_DETECTION = "anomaly_detection"
    CONTEXT_EMBEDDING = "context_embedding"

class ModelStatus(Enum):
    """Model lifecycle status"""
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UPDATING = "updating"
    CORRUPTED = "corrupted"

@dataclass
class ModelMetadata:
    """Metadata for AI models"""
    name: str
    version: str
    model_type: ModelType
    created_at: float
    updated_at: float
    file_size: int
    checksum: str
    parameters: Dict[str, Any]
    performance_metrics: Dict[str, float]
    hardware_requirements: Dict[str, Any]
    tags: List[str]
    dependencies: List[str]

@dataclass
class ModelInstance:
    """Runtime instance of a loaded model"""
    metadata: ModelMetadata
    model_object: Any
    status: ModelStatus
    load_time: float
    memory_usage: int
    last_used: float
    usage_count: int
    cache_score: float

class ModelOptimizer:
    """Optimizes AI models for better performance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_for_inference(self, model: torch.nn.Module) -> torch.nn.Module:
        """Optimize model for faster inference"""
        
        try:
            # Convert to evaluation mode
            model.eval()
            
            # Apply quantization if supported
            if hasattr(torch, 'quantization'):
                model = torch.quantization.quantize_dynamic(
                    model, {torch.nn.Linear}, dtype=torch.qint8
                )
                self.logger.info("Applied dynamic quantization")
            
            # Apply JIT compilation if supported
            try:
                # Create dummy input for tracing
                dummy_input = self._create_dummy_input(model)
                model = torch.jit.trace(model, dummy_input)
                self.logger.info("Applied JIT compilation")
            except Exception as e:
                self.logger.warning(f"JIT compilation failed: {e}")
            
            return model
            
        except Exception as e:
            self.logger.error(f"Model optimization failed: {e}")
            return model
    
    def _create_dummy_input(self, model: torch.nn.Module) -> torch.Tensor:
        """Create dummy input for model tracing"""
        # This is a simplified implementation
        # In production, would analyze model architecture
        return torch.randn(1, 3, 224, 224)
    
    def optimize_memory_usage(self, model: torch.nn.Module) -> torch.nn.Module:
        """Optimize model for reduced memory usage"""
        
        try:
            # Enable gradient checkpointing if available
            if hasattr(model, 'gradient_checkpointing_enable'):
                model.gradient_checkpointing_enable()
            
            # Use mixed precision if available
            if hasattr(torch, 'cuda') and torch.cuda.is_available():
                model = model.half()
                self.logger.info("Applied mixed precision")
            
            return model
            
        except Exception as e:
            self.logger.error(f"Memory optimization failed: {e}")
            return model

class ModelCache:
    """Intelligent caching system for AI models"""
    
    def __init__(self, max_cache_size: int = 4 * 1024 * 1024 * 1024):  # 4GB
        self.logger = logging.getLogger(__name__)
        self.max_cache_size = max_cache_size
        self.current_cache_size = 0
        self.cache: Dict[str, ModelInstance] = {}
        self.cache_lock = threading.RLock()
    
    def add_model(self, model_key: str, model_instance: ModelInstance):
        """Add model to cache with intelligent eviction"""
        
        with self.cache_lock:
            # Check if we need to evict models
            while (self.current_cache_size + model_instance.memory_usage > 
                   self.max_cache_size and self.cache):
                self._evict_least_useful_model()
            
            # Remove existing model if present
            if model_key in self.cache:
                self.current_cache_size -= self.cache[model_key].memory_usage
            
            # Add new model
            self.cache[model_key] = model_instance
            self.current_cache_size += model_instance.memory_usage
            
            self.logger.info(f"Added model {model_key} to cache. Cache size: {self.current_cache_size / 1024 / 1024:.1f}MB")
    
    def get_model(self, model_key: str) -> Optional[ModelInstance]:
        """Get model from cache and update usage statistics"""
        
        with self.cache_lock:
            if model_key in self.cache:
                model_instance = self.cache[model_key]
                model_instance.last_used = time.time()
                model_instance.usage_count += 1
                
                # Update cache score
                model_instance.cache_score = self._calculate_cache_score(model_instance)
                
                return model_instance
            
            return None
    
    def _evict_least_useful_model(self):
        """Evict the least useful model from cache"""
        
        if not self.cache:
            return
        
        # Find model with lowest cache score
        least_useful_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].cache_score
        )
        
        evicted_model = self.cache.pop(least_useful_key)
        self.current_cache_size -= evicted_model.memory_usage
        
        self.logger.info(f"Evicted model {least_useful_key} from cache")
    
    def _calculate_cache_score(self, model_instance: ModelInstance) -> float:
        """Calculate cache score based on usage patterns"""
        
        current_time = time.time()
        time_since_last_use = current_time - model_instance.last_used
        recency_factor = max(0, 1 - time_since_last_use / 3600)  # Decay over 1 hour
        
        frequency_factor = min(1, model_instance.usage_count / 100)  # Cap at 100 uses
        
        # Combine factors with weights
        cache_score = (recency_factor * 0.6 + frequency_factor * 0.4)
        
        return cache_score
    
    def clear_cache(self):
        """Clear all models from cache"""
        
        with self.cache_lock:
            self.cache.clear()
            self.current_cache_size = 0
            self.logger.info("Cleared model cache")

class ModelManager:
    """Central AI model management system"""
    
    def __init__(self, model_dir: str = "models"):
        self.logger = logging.getLogger(__name__)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.optimizer = ModelOptimizer()
        self.cache = ModelCache()
        
        # Model registry
        self.models: Dict[str, ModelMetadata] = {}
        self.loaded_models: Dict[str, ModelInstance] = {}
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict]] = {}
        
        # Load model registry
        self._load_registry()
        
        # Background optimization thread
        self.optimization_thread = None
        self.start_background_optimization()
    
    def _load_registry(self):
        """Load model registry from disk"""
        
        registry_file = self.model_dir / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                
                for model_data in registry_data:
                    metadata = ModelMetadata(**model_data)
                    self.models[f"{metadata.name}:{metadata.version}"] = metadata
                
                self.logger.info(f"Loaded {len(self.models)} models from registry")
                
            except Exception as e:
                self.logger.error(f"Failed to load model registry: {e}")
    
    def _save_registry(self):
        """Save model registry to disk"""
        
        registry_file = self.model_dir / "registry.json"
        try:
            registry_data = []
            for metadata in self.models.values():
                registry_data.append(asdict(metadata))
            
            with open(registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
            
            self.logger.info("Saved model registry to disk")
            
        except Exception as e:
            self.logger.error(f"Failed to save model registry: {e}")
    
    async def register_model(
        self,
        name: str,
        version: str,
        model_type: ModelType,
        model_path: str,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Register a new AI model"""
        
        try:
            model_path = Path(model_path)
            if not model_path.exists():
                self.logger.error(f"Model file not found: {model_path}")
                return False
            
            # Calculate file size and checksum
            file_size = model_path.stat().st_size
            checksum = self._calculate_checksum(model_path)
            
            # Create metadata
            metadata = ModelMetadata(
                name=name,
                version=version,
                model_type=model_type,
                created_at=time.time(),
                updated_at=time.time(),
                file_size=file_size,
                checksum=checksum,
                parameters=parameters or {},
                performance_metrics={},
                hardware_requirements={},
                tags=tags or [],
                dependencies=[]
            )
            
            # Copy model to model directory
            dest_path = self.model_dir / f"{name}_{version}.model"
            shutil.copy2(model_path, dest_path)
            
            # Update registry
            model_key = f"{name}:{version}"
            self.models[model_key] = metadata
            self._save_registry()
            
            self.logger.info(f"Registered model {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register model: {e}")
            return False
    
    async def load_model(
        self,
        name: str,
        version: Optional[str] = None,
        optimize: bool = True
    ) -> Optional[Any]:
        """Load a model by name and optional version"""
        
        model_key = self._find_model_key(name, version)
        if not model_key:
            self.logger.error(f"Model not found: {name}:{version}")
            return None
        
        # Check if already loaded in cache
        cached_model = self.cache.get_model(model_key)
        if cached_model:
            self.logger.info(f"Model {model_key} loaded from cache")
            return cached_model.model_object
        
        try:
            metadata = self.models[model_key]
            
            # Update status
            metadata.status = ModelStatus.LOADING
            self._save_registry()
            
            # Load model from disk
            model_path = self.model_dir / f"{name}_{metadata.version}.model"
            
            start_time = time.time()
            
            # Load based on model type
            if metadata.model_type in [ModelType.NLP_INTENT, ModelType.NLP_ENTITY]:
                model_object = await self._load_nlp_model(model_path, metadata)
            elif metadata.model_type in [ModelType.VISION_FACE, ModelType.VISION_GESTURE]:
                model_object = await self._load_vision_model(model_path, metadata)
            else:
                model_object = await self._load_generic_model(model_path, metadata)
            
            load_time = time.time() - start_time
            
            # Optimize model if requested
            if optimize and hasattr(model_object, '__class__'):
                model_object = self.optimizer.optimize_for_inference(model_object)
                model_object = self.optimizer.optimize_memory_usage(model_object)
            
            # Create model instance
            memory_usage = self._estimate_memory_usage(model_object)
            model_instance = ModelInstance(
                metadata=metadata,
                model_object=model_object,
                status=ModelStatus.LOADED,
                load_time=load_time,
                memory_usage=memory_usage,
                last_used=time.time(),
                usage_count=1,
                cache_score=1.0
            )
            
            # Update metadata
            metadata.status = ModelStatus.ACTIVE
            metadata.updated_at = time.time()
            metadata.performance_metrics["load_time"] = load_time
            
            # Cache the model
            self.cache.add_model(model_key, model_instance)
            self.loaded_models[model_key] = model_instance
            
            self._save_registry()
            
            self.logger.info(f"Loaded model {model_key} in {load_time:.2f}s")
            return model_object
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_key}: {e}")
            
            # Update status to error
            if model_key in self.models:
                self.models[model_key].status = ModelStatus.ERROR
                self._save_registry()
            
            return None
    
    async def _load_nlp_model(self, model_path: Path, metadata: ModelMetadata) -> Any:
        """Load NLP model (transformers, etc.)"""
        
        try:
            import transformers
            
            # Load transformer model
            model = transformers.AutoModel.from_pretrained(str(model_path))
            return model
            
        except ImportError:
            # Fallback to generic loading
            return await self._load_generic_model(model_path, metadata)
    
    async def _load_vision_model(self, model_path: Path, metadata: ModelMetadata) -> Any:
        """Load computer vision model"""
        
        try:
            import torch
            # Load PyTorch model
            model = torch.load(str(model_path), map_location='cpu')
            return model
            
        except ImportError:
            return await self._load_generic_model(model_path, metadata)
    
    async def _load_generic_model(self, model_path: Path, metadata: ModelMetadata) -> Any:
        """Load generic model using pickle or joblib"""
        
        try:
            import joblib
            return joblib.load(str(model_path))
        except ImportError:
            import pickle
            with open(model_path, 'rb') as f:
                return pickle.load(f)
    
    def _find_model_key(self, name: str, version: Optional[str] = None) -> Optional[str]:
        """Find model key by name and version"""
        
        if version:
            model_key = f"{name}:{version}"
            if model_key in self.models:
                return model_key
        else:
            # Find latest version
            matching_keys = [k for k in self.models.keys() if k.startswith(f"{name}:")]
            if matching_keys:
                # Return the most recently updated
                latest_key = max(
                    matching_keys,
                    key=lambda k: self.models[k].updated_at
                )
                return latest_key
        
        return None
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _estimate_memory_usage(self, model_object: Any) -> int:
        """Estimate memory usage of loaded model"""
        
        try:
            if hasattr(model_object, 'parameters'):
                # PyTorch model
                param_count = sum(p.numel() for p in model_object.parameters())
                # Rough estimate: 4 bytes per parameter (float32)
                return param_count * 4
            else:
                # Generic estimate based on object size
                import sys
                return sys.getsizeof(model_object)
        except:
            return 100 * 1024 * 1024  # 100MB default estimate
    
    async def unload_model(self, name: str, version: Optional[str] = None):
        """Unload a model from memory"""
        
        model_key = self._find_model_key(name, version)
        if not model_key:
            return
        
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
            
            # Remove from cache
            if hasattr(self.cache, 'cache') and model_key in self.cache.cache:
                self.cache.current_cache_size -= self.cache.cache[model_key].memory_usage
                del self.cache.cache[model_key]
            
            # Update metadata
            if model_key in self.models:
                self.models[model_key].status = ModelStatus.INACTIVE
                self._save_registry()
            
            self.logger.info(f"Unloaded model {model_key}")
    
    def start_background_optimization(self):
        """Start background optimization thread"""
        
        def optimization_loop():
            while True:
                try:
                    self._perform_background_optimization()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    self.logger.error(f"Background optimization error: {e}")
                    time.sleep(60)  # Wait before retry
        
        self.optimization_thread = threading.Thread(
            target=optimization_loop,
            daemon=True
        )
        self.optimization_thread.start()
    
    def _perform_background_optimization(self):
        """Perform background optimization tasks"""
        
        # Check memory usage and unload unused models
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > 80:
            self.logger.info("High memory usage detected, unloading unused models")
            
            # Find least recently used models
            sorted_models = sorted(
                self.loaded_models.items(),
                key=lambda x: x[1].last_used
            )
            
            # Unload oldest models until memory usage is acceptable
            for model_key, model_instance in sorted_models:
                if memory_usage < 70:
                    break
                
                time_since_use = time.time() - model_instance.last_used
                if time_since_use > 1800:  # 30 minutes
                    asyncio.create_task(self.unload_model(*model_key.split(":")))
                    memory_usage -= 5  # Estimate reduction
        
        # Update cache scores
        for model_instance in self.loaded_models.values():
            model_instance.cache_score = self.cache._calculate_cache_score(model_instance)
    
    def get_model_info(self, name: str, version: Optional[str] = None) -> Optional[Dict]:
        """Get information about a model"""
        
        model_key = self._find_model_key(name, version)
        if not model_key or model_key not in self.models:
            return None
        
        metadata = self.models[model_key]
        return asdict(metadata)
    
    def list_models(self, model_type: Optional[ModelType] = None) -> List[Dict]:
        """List all registered models"""
        
        models = []
        for metadata in self.models.values():
            if model_type is None or metadata.model_type == model_type:
                models.append(asdict(metadata))
        
        return models
    
    async def update_model_performance(
        self,
        name: str,
        version: str,
        metrics: Dict[str, float]
    ):
        """Update performance metrics for a model"""
        
        model_key = f"{name}:{version}"
        if model_key not in self.models:
            return
        
        metadata = self.models[model_key]
        metadata.performance_metrics.update(metrics)
        metadata.updated_at = time.time()
        
        # Track performance history
        if model_key not in self.performance_history:
            self.performance_history[model_key] = []
        
        self.performance_history[model_key].append({
            "timestamp": time.time(),
            "metrics": metrics.copy()
        })
        
        # Keep only last 100 entries
        if len(self.performance_history[model_key]) > 100:
            self.performance_history[model_key].pop(0)
        
        self._save_registry()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics for model management"""
        
        return {
            "total_models": len(self.models),
            "loaded_models": len(self.loaded_models),
            "cache_size_mb": self.cache.current_cache_size / 1024 / 1024,
            "cache_models": len(self.cache.cache),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "models_by_type": {
                model_type.value: len([
                    m for m in self.models.values() 
                    if m.model_type == model_type
                ])
                for model_type in ModelType
            }
        }

# Test the model manager
async def test_model_manager():
    """Test the model management system"""
    
    manager = ModelManager()
    
    # Create a dummy model for testing
    dummy_model_path = Path("test_model.model")
    dummy_model_path.write_text("dummy model data")
    
    try:
        # Register a model
        success = await manager.register_model(
            name="test_nlp",
            version="1.0.0",
            model_type=ModelType.NLP_INTENT,
            model_path=str(dummy_model_path),
            tags=["test", "nlp"]
        )
        
        print(f"Model registered: {success}")
        
        # List models
        models = manager.list_models()
        print(f"Total models: {len(models)}")
        
        # Get system stats
        stats = manager.get_system_stats()
        print(f"System stats: {stats}")
        
    finally:
        # Cleanup
        if dummy_model_path.exists():
            dummy_model_path.unlink()

if __name__ == "__main__":
    asyncio.run(test_model_manager())