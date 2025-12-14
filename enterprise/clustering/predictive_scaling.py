"""
Aurora OS AI-Powered Predictive Scaling Engine
Uses machine learning to predict scaling needs and optimize cluster performance
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import json
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
from pathlib import Path

from .cluster_orchestrator import ClusterMetrics, ScalingConfig

@dataclass
class PredictionResult:
    """Prediction result with confidence and recommendations"""
    predicted_cpu: float
    predicted_memory: float
    predicted_network: float
    predicted_request_rate: float
    confidence_score: float
    scaling_recommendation: str
    recommended_nodes: int
    prediction_horizon: int  # minutes
    model_version: str
    timestamp: datetime

@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    is_anomaly: bool
    anomaly_score: float
    affected_metrics: List[str]
    severity: str
    explanation: str

class PredictiveScalingEngine:
    """AI-powered predictive scaling engine"""
    
    def __init__(self, model_path: str = "/tmp/aurora_models"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Machine learning models
        self.cpu_model = None
        self.memory_model = None
        self.network_model = None
        self.request_rate_model = None
        self.anomaly_detector = None
        
        # Data preprocessing
        self.scaler_cpu = StandardScaler()
        self.scaler_memory = StandardScaler()
        self.scaler_network = StandardScaler()
        self.scaler_request_rate = StandardScaler()
        
        # Training data
        self.metrics_history: List[ClusterMetrics] = []
        self.training_data_path = self.model_path / "training_data.csv"
        
        # Model metadata
        self.model_version = "1.0.0"
        self.last_trained = None
        self.prediction_accuracy = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self.initialize_models()

    def initialize_models(self) -> None:
        """Initialize machine learning models"""
        try:
            # Load existing models if available
            self.load_models()
            
            if not self.cpu_model:
                # Initialize new models
                self.cpu_model = RandomForestRegressor(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
                
                self.memory_model = RandomForestRegressor(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
                
                self.network_model = RandomForestRegressor(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
                
                self.request_rate_model = RandomForestRegressor(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
                
                self.anomaly_detector = IsolationForest(
                    contamination=0.1,
                    random_state=42
                )
            
            self.logger.info("Predictive scaling models initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize models: {e}")
            self.initialize_fallback_models()

    def initialize_fallback_models(self) -> None:
        """Initialize fallback models for basic predictions"""
        self.cpu_model = None
        self.memory_model = None
        self.network_model = None
        self.request_rate_model = None
        self.anomaly_detector = None

    async def add_metrics(self, metrics: ClusterMetrics) -> None:
        """Add new metrics to the history"""
        self.metrics_history.append(metrics)
        
        # Keep only last 10000 data points
        if len(self.metrics_history) > 10000:
            self.metrics_history = self.metrics_history[-10000:]
        
        # Periodically retrain models
        if len(self.metrics_history) % 100 == 0 and len(self.metrics_history) >= 500:
            await self.retrain_models()

    async def predict_scaling_needs(self, 
                                   prediction_horizon: int = 60,
                                   current_metrics: Optional[ClusterMetrics] = None) -> PredictionResult:
        """Predict future scaling needs"""
        try:
            if not current_metrics and self.metrics_history:
                current_metrics = self.metrics_history[-1]
            
            if not current_metrics:
                # Return default prediction
                return self.get_default_prediction(prediction_horizon)
            
            # Prepare features for prediction
            features = self.prepare_prediction_features(current_metrics)
            
            # Make predictions
            predicted_cpu = await self.predict_cpu_usage(features, prediction_horizon)
            predicted_memory = await self.predict_memory_usage(features, prediction_horizon)
            predicted_network = await self.predict_network_usage(features, prediction_horizon)
            predicted_request_rate = await self.predict_request_rate(features, prediction_horizon)
            
            # Calculate confidence score
            confidence_score = self.calculate_prediction_confidence(features)
            
            # Generate scaling recommendation
            scaling_recommendation, recommended_nodes = self.generate_scaling_recommendation(
                predicted_cpu, predicted_memory, current_metrics.total_nodes
            )
            
            return PredictionResult(
                predicted_cpu=predicted_cpu,
                predicted_memory=predicted_memory,
                predicted_network=predicted_network,
                predicted_request_rate=predicted_request_rate,
                confidence_score=confidence_score,
                scaling_recommendation=scaling_recommendation,
                recommended_nodes=recommended_nodes,
                prediction_horizon=prediction_horizon,
                model_version=self.model_version,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return self.get_default_prediction(prediction_horizon)

    def prepare_prediction_features(self, current_metrics: ClusterMetrics) -> np.ndarray:
        """Prepare features for machine learning prediction"""
        # Use recent metrics history as features
        if len(self.metrics_history) < 24:  # Need at least 2 hours of data (30s intervals)
            return self.get_basic_features(current_metrics)
        
        recent_metrics = self.metrics_history[-24:]  # Last 2 hours
        features = []
        
        # Time-based features
        now = datetime.now()
        features.extend([
            now.hour,
            now.day_of_week,
            now.day,
            now.month,
            int(now.weekday() >= 5)  # Weekend flag
        ])
        
        # Current metrics
        features.extend([
            current_metrics.total_nodes,
            current_metrics.active_nodes,
            current_metrics.cpu_utilization,
            current_metrics.memory_utilization,
            current_metrics.network_throughput,
            current_metrics.request_rate,
            current_metrics.error_rate,
            current_metrics.response_time
        ])
        
        # Statistical features from recent history
        cpu_values = [m.cpu_utilization for m in recent_metrics]
        memory_values = [m.memory_utilization for m in recent_metrics]
        request_values = [m.request_rate for m in recent_metrics]
        
        # Add statistical features
        features.extend([
            np.mean(cpu_values),
            np.std(cpu_values),
            np.max(cpu_values),
            np.min(cpu_values),
            np.mean(memory_values),
            np.std(memory_values),
            np.max(memory_values),
            np.min(memory_values),
            np.mean(request_values),
            np.std(request_values),
            np.max(request_values),
            np.min(request_values)
        ])
        
        # Trend features (simple linear regression slope)
        features.extend([
            self.calculate_trend(cpu_values),
            self.calculate_trend(memory_values),
            self.calculate_trend(request_values)
        ])
        
        return np.array(features).reshape(1, -1)

    def get_basic_features(self, current_metrics: ClusterMetrics) -> np.ndarray:
        """Get basic features when insufficient history is available"""
        now = datetime.now()
        features = [
            now.hour,
            now.day_of_week,
            now.day,
            now.month,
            int(now.weekday() >= 5),
            current_metrics.total_nodes,
            current_metrics.active_nodes,
            current_metrics.cpu_utilization,
            current_metrics.memory_utilization,
            current_metrics.network_throughput,
            current_metrics.request_rate,
            current_metrics.error_rate,
            current_metrics.response_time
        ]
        
        # Add zero padding for missing statistical features
        features.extend([0.0] * 15)  # Pad to expected feature length
        
        return np.array(features).reshape(1, -1)

    def calculate_trend(self, values: List[float]) -> float:
        """Calculate simple linear trend (slope)"""
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Simple linear regression
        try:
            slope = np.polyfit(x, y, 1)[0]
            return slope
        except:
            return 0.0

    async def predict_cpu_usage(self, features: np.ndarray, horizon_minutes: int) -> float:
        """Predict CPU usage for given horizon"""
        try:
            if self.cpu_model and len(self.metrics_history) >= 100:
                # Scale features
                features_scaled = self.scaler_cpu.transform(features)
                
                # Make prediction
                prediction = self.cpu_model.predict(features_scaled)[0]
                
                # Apply horizon scaling (simple linear extrapolation)
                horizon_factor = 1 + (horizon_minutes / 60) * 0.1
                predicted_value = prediction * horizon_factor
                
                return max(0, min(100, predicted_value))
            else:
                # Fallback prediction
                current_cpu = features[0, 7] if features.shape[1] > 7 else 50
                trend = features[0, -3] if features.shape[1] >= 3 else 0
                predicted_cpu = current_cpu + trend * (horizon_minutes / 30)
                return max(0, min(100, predicted_cpu))
                
        except Exception as e:
            self.logger.error(f"CPU prediction failed: {e}")
            return 50.0  # Default fallback

    async def predict_memory_usage(self, features: np.ndarray, horizon_minutes: int) -> float:
        """Predict memory usage for given horizon"""
        try:
            if self.memory_model and len(self.metrics_history) >= 100:
                features_scaled = self.scaler_memory.transform(features)
                prediction = self.memory_model.predict(features_scaled)[0]
                
                # Apply horizon scaling
                horizon_factor = 1 + (horizon_minutes / 60) * 0.05
                predicted_value = prediction * horizon_factor
                
                return max(0, min(100, predicted_value))
            else:
                # Fallback prediction
                current_memory = features[0, 8] if features.shape[1] > 8 else 60
                trend = features[0, -2] if features.shape[1] >= 2 else 0
                predicted_memory = current_memory + trend * (horizon_minutes / 30)
                return max(0, min(100, predicted_memory))
                
        except Exception as e:
            self.logger.error(f"Memory prediction failed: {e}")
            return 60.0  # Default fallback

    async def predict_network_usage(self, features: np.ndarray, horizon_minutes: int) -> float:
        """Predict network throughput for given horizon"""
        try:
            if self.network_model and len(self.metrics_history) >= 100:
                features_scaled = self.scaler_network.transform(features)
                prediction = self.network_model.predict(features_scaled)[0]
                
                # Network usage is more volatile, apply appropriate scaling
                horizon_factor = 1 + (horizon_minutes / 60) * 0.15
                return max(0, prediction * horizon_factor)
            else:
                # Fallback prediction
                current_network = features[0, 9] if features.shape[1] > 9 else 1000
                return current_network * 1.1  # Simple 10% increase
                
        except Exception as e:
            self.logger.error(f"Network prediction failed: {e}")
            return 1000.0  # Default fallback

    async def predict_request_rate(self, features: np.ndarray, horizon_minutes: int) -> float:
        """Predict request rate for given horizon"""
        try:
            if self.request_rate_model and len(self.metrics_history) >= 100:
                features_scaled = self.scaler_request_rate.transform(features)
                prediction = self.request_rate_model.predict(features_scaled)[0]
                
                # Request rate varies based on time of day
                hour = features[0, 0] if features.shape[1] > 0 else 12
                time_factor = self.get_time_of_day_factor(hour)
                
                return max(0, prediction * time_factor)
            else:
                # Fallback prediction
                current_requests = features[0, 10] if features.shape[1] > 10 else 100
                hour = features[0, 0] if features.shape[1] > 0 else 12
                time_factor = self.get_time_of_day_factor(hour)
                return current_requests * time_factor
                
        except Exception as e:
            self.logger.error(f"Request rate prediction failed: {e}")
            return 100.0  # Default fallback

    def get_time_of_day_factor(self, hour: int) -> float:
        """Get request scaling factor based on time of day"""
        # Business hours (8 AM - 6 PM) have higher traffic
        if 8 <= hour <= 18:
            return 1.2
        elif 19 <= hour <= 23:  # Evening
            return 0.9
        else:  # Night (midnight - 7 AM)
            return 0.6

    def calculate_prediction_confidence(self, features: np.ndarray) -> float:
        """Calculate confidence score for predictions"""
        try:
            # Base confidence on data availability
            data_confidence = min(1.0, len(self.metrics_history) / 1000)
            
            # Model confidence (if models are trained)
            model_confidence = 0.5 if self.cpu_model else 0.3
            
            # Feature quality confidence
            feature_confidence = 0.8 if features.shape[1] > 20 else 0.6
            
            # Combined confidence
            overall_confidence = (data_confidence + model_confidence + feature_confidence) / 3
            
            return min(0.95, max(0.1, overall_confidence))
            
        except:
            return 0.5  # Default confidence

    def generate_scaling_recommendation(self, 
                                       predicted_cpu: float, 
                                       predicted_memory: float,
                                       current_nodes: int,
                                       cpu_threshold: float = 80.0,
                                       memory_threshold: float = 85.0) -> Tuple[str, int]:
        """Generate scaling recommendation based on predictions"""
        
        # Scale up needed
        if predicted_cpu > cpu_threshold or predicted_memory > memory_threshold:
            if predicted_cpu > 95 or predicted_memory > 95:
                return "immediate_scale_up", current_nodes + 3
            elif predicted_cpu > 90 or predicted_memory > 90:
                return "urgent_scale_up", current_nodes + 2
            else:
                return "moderate_scale_up", current_nodes + 1
        
        # Scale down possible
        elif predicted_cpu < cpu_threshold * 0.4 and predicted_memory < memory_threshold * 0.4:
            if current_nodes > 3:
                return "scale_down", max(3, current_nodes - 1)
            else:
                return "maintain", current_nodes
        
        # No scaling needed
        else:
            return "maintain", current_nodes

    def get_default_prediction(self, prediction_horizon: int) -> PredictionResult:
        """Get default prediction when models are not available"""
        return PredictionResult(
            predicted_cpu=60.0,
            predicted_memory=65.0,
            predicted_network=1000.0,
            predicted_request_rate=100.0,
            confidence_score=0.3,
            scaling_recommendation="maintain",
            recommended_nodes=3,
            prediction_horizon=prediction_horizon,
            model_version="fallback",
            timestamp=datetime.now()
        )

    async def detect_anomalies(self, current_metrics: ClusterMetrics) -> AnomalyDetection:
        """Detect anomalies in current metrics"""
        try:
            if not self.anomaly_detector or len(self.metrics_history) < 50:
                return AnomalyDetection(
                    is_anomaly=False,
                    anomaly_score=0.0,
                    affected_metrics=[],
                    severity="low",
                    explanation="Insufficient data for anomaly detection"
                )
            
            # Prepare features for anomaly detection
            features = self.prepare_anomaly_features(current_metrics)
            
            # Detect anomaly
            anomaly_score = self.anomaly_detector.decision_function(features)[0]
            is_anomaly = anomaly_score < 0
            
            # Identify affected metrics
            affected_metrics = []
            if is_anomaly:
                affected_metrics = self.identify_anomalous_metrics(current_metrics)
            
            # Determine severity
            severity = self.calculate_anomaly_severity(anomaly_score, affected_metrics)
            
            # Generate explanation
            explanation = self.generate_anomaly_explanation(affected_metrics, current_metrics)
            
            return AnomalyDetection(
                is_anomaly=is_anomaly,
                anomaly_score=abs(anomaly_score),
                affected_metrics=affected_metrics,
                severity=severity,
                explanation=explanation
            )
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            return AnomalyDetection(
                is_anomaly=False,
                anomaly_score=0.0,
                affected_metrics=[],
                severity="low",
                explanation="Anomaly detection service unavailable"
            )

    def prepare_anomaly_features(self, current_metrics: ClusterMetrics) -> np.ndarray:
        """Prepare features for anomaly detection"""
        features = [
            current_metrics.total_nodes,
            current_metrics.active_nodes,
            current_metrics.cpu_utilization,
            current_metrics.memory_utilization,
            current_metrics.network_throughput,
            current_metrics.request_rate,
            current_metrics.error_rate,
            current_metrics.response_time
        ]
        
        # Add statistical features if history available
        if len(self.metrics_history) >= 10:
            recent_metrics = self.metrics_history[-10:]
            
            cpu_values = [m.cpu_utilization for m in recent_metrics]
            memory_values = [m.memory_utilization for m in recent_metrics]
            request_values = [m.request_rate for m in recent_metrics]
            
            features.extend([
                np.std(cpu_values),
                np.std(memory_values),
                np.std(request_values),
                np.mean(cpu_values) - current_metrics.cpu_utilization,
                np.mean(memory_values) - current_metrics.memory_utilization,
                np.mean(request_values) - current_metrics.request_rate
            ])
        else:
            features.extend([0.0] * 6)
        
        return np.array(features).reshape(1, -1)

    def identify_anomalous_metrics(self, current_metrics: ClusterMetrics) -> List[str]:
        """Identify which metrics are anomalous"""
        anomalous_metrics = []
        threshold = 2.0  # Standard deviations
        
        if len(self.metrics_history) >= 20:
            recent_metrics = self.metrics_history[-20:]
            
            # Check CPU utilization
            cpu_values = [m.cpu_utilization for m in recent_metrics]
            cpu_mean, cpu_std = np.mean(cpu_values), np.std(cpu_values)
            if abs(current_metrics.cpu_utilization - cpu_mean) > threshold * cpu_std:
                anomalous_metrics.append("cpu_utilization")
            
            # Check memory utilization
            memory_values = [m.memory_utilization for m in recent_metrics]
            memory_mean, memory_std = np.mean(memory_values), np.std(memory_values)
            if abs(current_metrics.memory_utilization - memory_mean) > threshold * memory_std:
                anomalous_metrics.append("memory_utilization")
            
            # Check error rate
            error_values = [m.error_rate for m in recent_metrics]
            error_mean, error_std = np.mean(error_values), np.std(error_values)
            if abs(current_metrics.error_rate - error_mean) > threshold * error_std:
                anomalous_metrics.append("error_rate")
            
            # Check response time
            response_values = [m.response_time for m in recent_metrics]
            response_mean, response_std = np.mean(response_values), np.std(response_values)
            if abs(current_metrics.response_time - response_mean) > threshold * response_std:
                anomalous_metrics.append("response_time")
        
        return anomalous_metrics

    def calculate_anomaly_severity(self, anomaly_score: float, affected_metrics: List[str]) -> str:
        """Calculate anomaly severity"""
        if len(affected_metrics) >= 3 or anomaly_score > 0.5:
            return "high"
        elif len(affected_metrics) >= 2 or anomaly_score > 0.3:
            return "medium"
        else:
            return "low"

    def generate_anomaly_explanation(self, affected_metrics: List[str], current_metrics: ClusterMetrics) -> str:
        """Generate explanation for anomaly detection"""
        if not affected_metrics:
            return "No anomalies detected"
        
        explanations = []
        for metric in affected_metrics:
            if metric == "cpu_utilization":
                explanations.append(f"CPU usage ({current_metrics.cpu_utilization:.1f}%) is unusual")
            elif metric == "memory_utilization":
                explanations.append(f"Memory usage ({current_metrics.memory_utilization:.1f}%) is unusual")
            elif metric == "error_rate":
                explanations.append(f"Error rate ({current_metrics.error_rate:.2f}%) is unusual")
            elif metric == "response_time":
                explanations.append(f"Response time ({current_metrics.response_time:.0f}ms) is unusual")
        
        return "; ".join(explanations)

    async def retrain_models(self) -> bool:
        """Retrain machine learning models with current data"""
        try:
            if len(self.metrics_history) < 500:
                self.logger.info("Insufficient data for model retraining")
                return False
            
            self.logger.info("Starting model retraining...")
            
            # Prepare training data
            X, y_cpu, y_memory, y_network, y_request_rate = self.prepare_training_data()
            
            if len(X) < 100:
                self.logger.warning("Insufficient training samples")
                return False
            
            # Split data for validation
            X_train, X_test, y_cpu_train, y_cpu_test = train_test_split(
                X, y_cpu, test_size=0.2, random_state=42
            )
            
            # Train CPU model
            self.cpu_model.fit(X_train, y_cpu_train)
            cpu_score = self.cpu_model.score(X_test, y_cpu_test)
            self.prediction_accuracy["cpu"] = cpu_score
            
            # Train memory model
            self.memory_model.fit(X_train, y_memory_train)
            memory_score = self.memory_model.score(X_test, y_memory_test)
            self.prediction_accuracy["memory"] = memory_score
            
            # Train network model
            self.network_model.fit(X_train, y_network_train)
            network_score = self.network_model.score(X_test, y_network_test)
            self.prediction_accuracy["network"] = network_score
            
            # Train request rate model
            self.request_rate_model.fit(X_train, y_request_rate_train)
            request_score = self.request_rate_model.score(X_test, y_request_rate_test)
            self.prediction_accuracy["request_rate"] = request_score
            
            # Train anomaly detector
            self.anomaly_detector.fit(X)
            
            # Update model metadata
            self.last_trained = datetime.now()
            self.model_version = f"1.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Save models
            self.save_models()
            
            self.logger.info(f"Model retraining completed. CPU: {cpu_score:.3f}, Memory: {memory_score:.3f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Model retraining failed: {e}")
            return False

    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data from metrics history"""
        X = []
        y_cpu = []
        y_memory = []
        y_network = []
        y_request_rate = []
        
        # Use sliding window approach
        window_size = 12  # 6 minutes of historical data (12 * 30s)
        prediction_horizon = 4  # 2 minutes ahead
        
        for i in range(window_size, len(self.metrics_history) - prediction_horizon):
            # Features from historical window
            window_metrics = self.metrics_history[i-window_size:i]
            features = self.extract_features_from_window(window_metrics)
            
            # Target values from future
            future_metrics = self.metrics_history[i + prediction_horizon]
            
            X.append(features)
            y_cpu.append(future_metrics.cpu_utilization)
            y_memory.append(future_metrics.memory_utilization)
            y_network.append(future_metrics.network_throughput)
            y_request_rate.append(future_metrics.request_rate)
        
        return (
            np.array(X),
            np.array(y_cpu),
            np.array(y_memory),
            np.array(y_network),
            np.array(y_request_rate)
        )

    def extract_features_from_window(self, window_metrics: List[ClusterMetrics]) -> List[float]:
        """Extract features from a window of metrics"""
        if not window_metrics:
            return [0.0] * 30
        
        # Time features
        timestamp = window_metrics[-1].timestamp
        features = [
            timestamp.hour,
            timestamp.day_of_week,
            timestamp.day,
            timestamp.month,
            int(timestamp.weekday() >= 5)
        ]
        
        # Current metrics
        current = window_metrics[-1]
        features.extend([
            current.total_nodes,
            current.active_nodes,
            current.cpu_utilization,
            current.memory_utilization,
            current.network_throughput,
            current.request_rate,
            current.error_rate,
            current.response_time
        ])
        
        # Statistical features
        cpu_values = [m.cpu_utilization for m in window_metrics]
        memory_values = [m.memory_utilization for m in window_metrics]
        request_values = [m.request_rate for m in window_metrics]
        error_values = [m.error_rate for m in window_metrics]
        response_values = [m.response_time for m in window_metrics]
        
        for values in [cpu_values, memory_values, request_values, error_values, response_values]:
            features.extend([
                np.mean(values),
                np.std(values),
                np.max(values),
                np.min(values)
            ])
        
        return features

    def save_models(self) -> None:
        """Save trained models to disk"""
        try:
            # Save machine learning models
            joblib.dump(self.cpu_model, self.model_path / "cpu_model.pkl")
            joblib.dump(self.memory_model, self.model_path / "memory_model.pkl")
            joblib.dump(self.network_model, self.model_path / "network_model.pkl")
            joblib.dump(self.request_rate_model, self.model_path / "request_rate_model.pkl")
            joblib.dump(self.anomaly_detector, self.model_path / "anomaly_detector.pkl")
            
            # Save scalers
            joblib.dump(self.scaler_cpu, self.model_path / "scaler_cpu.pkl")
            joblib.dump(self.scaler_memory, self.model_path / "scaler_memory.pkl")
            joblib.dump(self.scaler_network, self.model_path / "scaler_network.pkl")
            joblib.dump(self.scaler_request_rate, self.model_path / "scaler_request_rate.pkl")
            
            # Save metadata
            metadata = {
                "model_version": self.model_version,
                "last_trained": self.last_trained.isoformat() if self.last_trained else None,
                "prediction_accuracy": self.prediction_accuracy
            }
            
            with open(self.model_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info("Models saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save models: {e}")

    def load_models(self) -> None:
        """Load trained models from disk"""
        try:
            # Load machine learning models
            self.cpu_model = joblib.load(self.model_path / "cpu_model.pkl")
            self.memory_model = joblib.load(self.model_path / "memory_model.pkl")
            self.network_model = joblib.load(self.model_path / "network_model.pkl")
            self.request_rate_model = joblib.load(self.model_path / "request_rate_model.pkl")
            self.anomaly_detector = joblib.load(self.model_path / "anomaly_detector.pkl")
            
            # Load scalers
            self.scaler_cpu = joblib.load(self.model_path / "scaler_cpu.pkl")
            self.scaler_memory = joblib.load(self.model_path / "scaler_memory.pkl")
            self.scaler_network = joblib.load(self.model_path / "scaler_network.pkl")
            self.scaler_request_rate = joblib.load(self.model_path / "scaler_request_rate.pkl")
            
            # Load metadata
            with open(self.model_path / "metadata.json", "r") as f:
                metadata = json.load(f)
                self.model_version = metadata.get("model_version", "1.0.0")
                self.prediction_accuracy = metadata.get("prediction_accuracy", {})
            
            self.logger.info("Models loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to load models: {e}")
            self.initialize_fallback_models()

    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status and performance"""
        return {
            "model_version": self.model_version,
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "data_points": len(self.metrics_history),
            "prediction_accuracy": self.prediction_accuracy,
            "models_available": {
                "cpu": self.cpu_model is not None,
                "memory": self.memory_model is not None,
                "network": self.network_model is not None,
                "request_rate": self.request_rate_model is not None,
                "anomaly_detector": self.anomaly_detector is not None
            }
        }