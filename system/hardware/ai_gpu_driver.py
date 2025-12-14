"""
Aurora OS AI GPU Driver Integration
Provides hardware acceleration for AI workloads on NVIDIA, AMD, and Intel GPUs
"""

import os
import sys
import json
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GPUInfo:
    """GPU device information"""
    vendor: str
    model: str
    memory_mb: int
    compute_capability: str
    driver_version: str
    cuda_capability: bool = False
    rocm_capability: bool = False
    opencl_capability: bool = False
    vulkan_capability: bool = False

class AIGPUDriver:
    """AI GPU Driver Manager for Aurora OS"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detected_gpus: List[GPUInfo] = []
        self.driver_configs = {}
        self.performance_profiles = {
            'inference': {
                'power_limit': 250,
                'memory_clock': 7000,
                'graphics_clock': 1500,
                'fan_speed': 'auto'
            },
            'training': {
                'power_limit': 350,
                'memory_clock': 8000,
                'graphics_clock': 1800,
                'fan_speed': 80
            },
            'balanced': {
                'power_limit': 200,
                'memory_clock': 6000,
                'graphics_clock': 1200,
                'fan_speed': 'auto'
            },
            'power_save': {
                'power_limit': 100,
                'memory_clock': 4000,
                'graphics_clock': 800,
                'fan_speed': 40
            }
        }
        
    def detect_gpus(self) -> List[GPUInfo]:
        """Detect available GPUs and their capabilities"""
        self.logger.info("Detecting GPUs...")
        
        # Detect NVIDIA GPUs
        nvidia_gpus = self._detect_nvidia_gpus()
        self.detected_gpus.extend(nvidia_gpus)
        
        # Detect AMD GPUs
        amd_gpus = self._detect_amd_gpus()
        self.detected_gpus.extend(amd_gpus)
        
        # Detect Intel GPUs
        intel_gpus = self._detect_intel_gpus()
        self.detected_gpus.extend(intel_gpus)
        
        self.logger.info(f"Detected {len(self.detected_gpus)} GPU(s)")
        return self.detected_gpus
    
    def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        """Detect NVIDIA GPUs"""
        gpus = []
        
        try:
            # Use nvidia-smi to detect GPUs
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version,compute_cap', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for i, line in enumerate(result.stdout.strip().split('\n')):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 4:
                            gpu = GPUInfo(
                                vendor='NVIDIA',
                                model=parts[0],
                                memory_mb=int(parts[1]),
                                compute_capability=parts[3],
                                driver_version=parts[2],
                                cuda_capability=True,
                                opencl_capability=True,
                                vulkan_capability=True
                            )
                            gpus.append(gpu)
                            self.logger.info(f"NVIDIA GPU {i}: {gpu.model} ({gpu.memory_mb}MB)")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Try alternative detection methods
            pass
        
        # Try detection via PCI
        try:
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '10de:' in line and 'VGA' in line:
                        # Parse NVIDIA PCI device
                        gpu = GPUInfo(
                            vendor='NVIDIA',
                            model='NVIDIA GPU (PCI detected)',
                            memory_mb=0,  # Unknown
                            compute_capability='Unknown',
                            driver_version='Unknown',
                            cuda_capability=True,
                            opencl_capability=True
                        )
                        if gpu not in gpus:
                            gpus.append(gpu)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return gpus
    
    def _detect_amd_gpus(self) -> List[GPUInfo]:
        """Detect AMD GPUs"""
        gpus = []
        
        try:
            # Use rocm-smi to detect GPUs
            result = subprocess.run(['rocm-smi', '--showproductname'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Card series' in line or 'GPU' in line:
                        # Extract GPU model information
                        model = line.split(':')[-1].strip() if ':' in line else 'AMD GPU'
                        gpu = GPUInfo(
                            vendor='AMD',
                            model=model,
                            memory_mb=0,  # Would need additional commands
                            compute_capability='Unknown',
                            driver_version='ROCm',
                            rocm_capability=True,
                            opencl_capability=True,
                            vulkan_capability=True
                        )
                        gpus.append(gpu)
                        self.logger.info(f"AMD GPU: {gpu.model}")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try detection via PCI
        try:
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '1002:' in line and 'VGA' in line:
                        gpu = GPUInfo(
                            vendor='AMD',
                            model='AMD GPU (PCI detected)',
                            memory_mb=0,
                            compute_capability='Unknown',
                            driver_version='Unknown',
                            rocm_capability=True,
                            opencl_capability=True
                        )
                        if gpu not in gpus:
                            gpus.append(gpu)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return gpus
    
    def _detect_intel_gpus(self) -> List[GPUInfo]:
        """Detect Intel GPUs"""
        gpus = []
        
        try:
            # Use Intel GPU tools
            result = subprocess.run(['intel_gpu_top', '-J'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Parse JSON output for GPU info
                try:
                    data = json.loads(result.stdout)
                    if 'platform' in data:
                        gpu = GPUInfo(
                            vendor='Intel',
                            model=data['platform'].get('name', 'Intel GPU'),
                            memory_mb=0,  # Integrated GPU
                            compute_capability='Unknown',
                            driver_version='Intel',
                            opencl_capability=True,
                            vulkan_capability=True
                        )
                        gpus.append(gpu)
                        self.logger.info(f"Intel GPU: {gpu.model}")
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try detection via PCI
        try:
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '8086:' in line and 'VGA' in line:
                        gpu = GPUInfo(
                            vendor='Intel',
                            model='Intel GPU (PCI detected)',
                            memory_mb=0,
                            compute_capability='Unknown',
                            driver_version='Unknown',
                            opencl_capability=True,
                            vulkan_capability=True
                        )
                        if gpu not in gpus:
                            gpus.append(gpu)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return gpus
    
    def install_drivers(self) -> bool:
        """Install appropriate GPU drivers"""
        self.logger.info("Installing GPU drivers...")
        success = True
        
        for gpu in self.detected_gpus:
            if gpu.vendor == 'NVIDIA':
                success &= self._install_nvidia_driver(gpu)
            elif gpu.vendor == 'AMD':
                success &= self._install_amd_driver(gpu)
            elif gpu.vendor == 'Intel':
                success &= self._install_intel_driver(gpu)
        
        return success
    
    def _install_nvidia_driver(self, gpu: GPUInfo) -> bool:
        """Install NVIDIA driver"""
        try:
            self.logger.info(f"Installing NVIDIA driver for {gpu.model}")
            
            # Check if nvidia driver is already loaded
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
            if result.returncode == 0:
                self.logger.info("NVIDIA driver already installed")
                return True
            
            # Install driver using package manager
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'nvidia-driver-535'], check=True)
            
            # Load kernel modules
            subprocess.run(['modprobe', 'nvidia'], check=True)
            subprocess.run(['modprobe', 'nvidia_uvm'], check=True)
            
            self.logger.info("NVIDIA driver installed successfully")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Failed to install NVIDIA driver: {e}")
            return False
    
    def _install_amd_driver(self, gpu: GPUInfo) -> bool:
        """Install AMD driver"""
        try:
            self.logger.info(f"Installing AMD driver for {gpu.model}")
            
            # Check if ROCm is available
            result = subprocess.run(['rocm-smi'], capture_output=True, timeout=5)
            if result.returncode == 0:
                self.logger.info("AMD ROCm driver already installed")
                return True
            
            # Install ROCm packages
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'rocm-dkms'], check=True)
            
            # Add user to render group
            subprocess.run(['usermod', '-a', '-G', 'render', 'aurora'], check=True)
            
            # Load kernel modules
            subprocess.run(['modprobe', 'amdgpu'], check=True)
            
            self.logger.info("AMD ROCm driver installed successfully")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Failed to install AMD driver: {e}")
            return False
    
    def _install_intel_driver(self, gpu: GPUInfo) -> bool:
        """Install Intel driver"""
        try:
            self.logger.info(f"Installing Intel driver for {gpu.model}")
            
            # Install Intel GPU packages
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'intel-media-va-driver', 'intel-gpu-tools'], check=True)
            
            # Load kernel modules
            subprocess.run(['modprobe', 'i915'], check=True)
            
            self.logger.info("Intel driver installed successfully")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Failed to install Intel driver: {e}")
            return False
    
    def optimize_for_ai(self, workload_type: str = 'inference') -> bool:
        """Optimize GPU settings for AI workloads"""
        if workload_type not in self.performance_profiles:
            workload_type = 'balanced'
        
        profile = self.performance_profiles[workload_type]
        success = True
        
        for gpu in self.detected_gpus:
            if gpu.vendor == 'NVIDIA':
                success &= self._optimize_nvidia_gpu(gpu, profile)
            elif gpu.vendor == 'AMD':
                success &= self._optimize_amd_gpu(gpu, profile)
            elif gpu.vendor == 'Intel':
                success &= self._optimize_intel_gpu(gpu, profile)
        
        return success
    
    def _optimize_nvidia_gpu(self, gpu: GPUInfo, profile: Dict) -> bool:
        """Optimize NVIDIA GPU settings"""
        try:
            # Set power limit
            subprocess.run(['nvidia-smi', '-i', '0', '-pl', str(profile['power_limit'])], check=True)
            
            # Set performance mode
            subprocess.run(['nvidia-smi', '-i', '0', '-ac', '877,1215'], check=True)
            
            self.logger.info(f"NVIDIA GPU optimized for {profile}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _optimize_amd_gpu(self, gpu: GPUInfo, profile: Dict) -> bool:
        """Optimize AMD GPU settings"""
        try:
            # Set performance level
            subprocess.run(['rocm-smi', '--setperflevel', 'high'], check=True)
            
            self.logger.info(f"AMD GPU optimized for {profile}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _optimize_intel_gpu(self, gpu: GPUInfo, profile: Dict) -> bool:
        """Optimize Intel GPU settings"""
        try:
            # Intel integrated GPUs have limited optimization options
            # Set power management profile
            with open('/sys/class/drm/card0/device/power_method', 'w') as f:
                f.write('performance')
            
            self.logger.info(f"Intel GPU optimized for {profile}")
            return True
            
        except (IOError, OSError):
            return False
    
    def get_gpu_status(self) -> Dict:
        """Get current GPU status and performance metrics"""
        status = {
            'total_gpus': len(self.detected_gpus),
            'gpus': []
        }
        
        for i, gpu in enumerate(self.detected_gpus):
            gpu_status = {
                'id': i,
                'vendor': gpu.vendor,
                'model': gpu.model,
                'memory_mb': gpu.memory_mb,
                'capabilities': {
                    'cuda': gpu.cuda_capability,
                    'rocm': gpu.rocm_capability,
                    'opencl': gpu.opencl_capability,
                    'vulkan': gpu.vulkan_capability
                }
            }
            
            # Get real-time metrics if available
            if gpu.vendor == 'NVIDIA':
                gpu_status.update(self._get_nvidia_metrics())
            elif gpu.vendor == 'AMD':
                gpu_status.update(self._get_amd_metrics())
            elif gpu.vendor == 'Intel':
                gpu_status.update(self._get_intel_metrics())
            
            status['gpus'].append(gpu_status)
        
        return status
    
    def _get_nvidia_metrics(self) -> Dict:
        """Get NVIDIA GPU metrics"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                values = result.stdout.strip().split(',')
                if len(values) >= 6:
                    return {
                        'gpu_utilization': int(values[0]),
                        'memory_utilization': int(values[1]),
                        'memory_used_mb': int(values[2]),
                        'memory_total_mb': int(values[3]),
                        'temperature_c': int(values[4]),
                        'power_watts': float(values[5])
                    }
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
            pass
        
        return {}
    
    def _get_amd_metrics(self) -> Dict:
        """Get AMD GPU metrics"""
        try:
            result = subprocess.run(['rocm-smi', '--showuse', '--showmemuse', '--showtemp', '--showpower'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Parse ROCm output
                metrics = {}
                for line in result.stdout.split('\n'):
                    if 'GPU Utilization' in line:
                        metrics['gpu_utilization'] = int(line.split('%')[0].split()[-1])
                    elif 'GPU Memory Usage' in line:
                        mem_parts = line.split()
                        if len(mem_parts) >= 3:
                            used = int(mem_parts[1].replace('MB', ''))
                            total = int(mem_parts[3].replace('MB', ''))
                            metrics['memory_used_mb'] = used
                            metrics['memory_total_mb'] = total
                            metrics['memory_utilization'] = int((used / total) * 100)
                
                return metrics
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
            pass
        
        return {}
    
    def _get_intel_metrics(self) -> Dict:
        """Get Intel GPU metrics"""
        try:
            result = subprocess.run(['intel_gpu_top', '-J'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    'gpu_utilization': data.get('busy', 0),
                    'render_utilization': data.get('render busy', 0),
                    'memory_utilization': data.get('memory busy', 0)
                }
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError):
            pass
        
        return {}

def main():
    """Main function for testing the AI GPU driver"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Aurora OS AI GPU Driver')
    parser.add_argument('--detect', action='store_true', help='Detect GPUs')
    parser.add_argument('--install', action='store_true', help='Install drivers')
    parser.add_argument('--optimize', choices=['inference', 'training', 'balanced', 'power_save'], 
                       help='Optimize for workload type')
    parser.add_argument('--status', action='store_true', help='Show GPU status')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    driver = AIGPUDriver()
    
    if args.detect:
        gpus = driver.detect_gpus()
        for gpu in gpus:
            print(f"{gpu.vendor} {gpu.model} ({gpu.memory_mb}MB)")
    
    if args.install:
        success = driver.install_drivers()
        print(f"Driver installation: {'Success' if success else 'Failed'}")
    
    if args.optimize:
        success = driver.optimize_for_ai(args.optimize)
        print(f"Optimization: {'Success' if success else 'Failed'}")
    
    if args.status:
        status = driver.get_gpu_status()
        print(json.dumps(status, indent=2))

if __name__ == '__main__':
    main()