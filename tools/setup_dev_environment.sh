#!/bin/bash

# Aurora OS Development Environment Setup Script
# Sets up the complete development environment for Aurora OS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Get Aurora OS root directory
AURORA_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$AURORA_ROOT"

print_status "Setting up Aurora OS development environment..."
print_status "Aurora OS root: $AURORA_ROOT"

# Create necessary directories
print_status "Creating directory structure..."
mkdir -p build/{kernel,system,ai,mcp,desktop,dist,docs}
mkdir -p tests/{kernel,system,ai,mcp,integration,e2e}
mkdir -p logs
mkdir -p cache
mkdir -p tmp

print_success "Directory structure created"

# Check system requirements
print_status "Checking system requirements..."

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    print_success "Linux detected"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    print_warning "macOS detected - some features may be limited"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check GCC
if command -v gcc &> /dev/null; then
    GCC_VERSION=$(gcc --version | head -n1)
    print_success "GCC found: $GCC_VERSION"
else
    print_error "GCC is required but not installed"
    exit 1
fi

# Check Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    print_success "Git found: $GIT_VERSION"
else
    print_error "Git is required but not installed"
    exit 1
fi

# Check Make
if command -v make &> /dev/null; then
    MAKE_VERSION=$(make --version | head -n1)
    print_success "Make found: $MAKE_VERSION"
else
    print_error "Make is required but not installed"
    exit 1
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install --user -r requirements.txt || {
    print_warning "requirements.txt not found, creating basic one..."
    cat > requirements.txt << EOF
# Aurora OS Python Dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
black>=22.0.0
flake8>=5.0.0
mypy>=1.0.0
sphinx>=5.0.0
sphinx-rtd-theme>=1.0.0
asyncio-mqtt>=0.13.0
aiofiles>=22.0.0
pydantic>=1.10.0
fastapi>=0.95.0
uvicorn>=0.20.0
websockets>=11.0.0
numpy>=1.24.0
scikit-learn>=1.2.0
nltk>=3.8.0
spacy>=3.6.0
transformers>=4.26.0
torch>=2.0.0
opencv-python>=4.7.0
pillow>=9.4.0
cryptography>=40.0.0
paramiko>=3.1.0
psutil>=5.9.0
python-magic>=0.4.27
EOF
    pip3 install --user -r requirements.txt
}

print_success "Python dependencies installed"

# Set up kernel development environment
print_status "Setting up kernel development environment..."

# Check if kernel headers are available
if [[ -d "/usr/src/linux-headers-$(uname -r)" ]]; then
    print_success "Kernel headers found"
else
    print_warning "Kernel headers not found, installing may be required"
fi

# Create kernel module build directory
mkdir -p kernel/ai_extensions/build
cd kernel/ai_extensions

# Create Makefile for kernel modules if not exists
if [[ ! -f "Makefile" ]]; then
    cat > Makefile << 'EOF'
obj-m += ai_scheduler.o
obj-m += context_manager.o
obj-m += ai_security.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean

install:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules_install

.PHONY: all clean install
EOF
fi

cd "$AURORA_ROOT"
print_success "Kernel development environment configured"

# Set up Python virtual environment
print_status "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create activation script
cat > activate_aurora.sh << 'EOF'
#!/bin/bash
# Aurora OS Development Environment Activation Script

AURORA_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export AURORA_ROOT="$AURORA_ROOT"
export AURORA_BUILD_DIR="$AURORA_ROOT/build"
export AURORA_VERSION="1.0.0"
export PYTHONPATH="$AURORA_ROOT:$AURORA_ROOT/system:$AURORA_ROOT/ai:$AURORA_ROOT/mcp:$AURORA_ROOT/desktop:$PYTHONPATH"

# Activate virtual environment
source "$AURORA_ROOT/venv/bin/activate"

echo "Aurora OS development environment activated!"
echo "AURORA_ROOT: $AURORA_ROOT"
echo "AURORA_VERSION: $AURORA_VERSION"
echo "Python: $(python --version)"
EOF

chmod +x activate_aurora.sh
print_success "Python virtual environment created"

# Set up Git configuration
print_status "Setting up Git configuration..."

# Create .gitignore if not exists
if [[ ! -f ".gitignore" ]]; then
    cat > .gitignore << 'EOF'
# Build artifacts
build/
dist/
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# Kernel build artifacts
*.ko
*.mod.c
*.mod.o
.modules.order
Module.symvers
.cmd
.tmp_versions/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Aurora OS specific
logs/
cache/
tmp/
*.pid
*.socket
*.lock

# Test files
test_results/
coverage_reports/
EOF
fi

# Set up pre-commit hooks
mkdir -p .git/hooks

cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Aurora OS pre-commit hook

echo "Running pre-commit checks..."

# Check Python formatting
python -m black --check .
if [[ $? -ne 0 ]]; then
    echo "Python code formatting check failed. Run 'make format' to fix."
    exit 1
fi

# Run linting
python -m flake8 .
if [[ $? -ne 0 ]]; then
    echo "Python linting failed. Please fix the issues."
    exit 1
fi

# Run tests
python -m pytest tests/ -v
if [[ $? -ne 0 ]]; then
    echo "Tests failed. Please fix the failing tests."
    exit 1
fi

echo "Pre-commit checks passed!"
EOF

chmod +x .git/hooks/pre-commit

print_success "Git configuration completed"

# Set up development tools
print_status "Setting up development tools..."

# Create development scripts directory
mkdir -p tools/dev

# Create development server script
cat > tools/dev_server.py << 'EOF'
#!/usr/bin/env python3
"""
Aurora OS Development Server
Provides development tools and services
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add Aurora OS to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.system.mcp_host import aurora_mcp_host
from system.ai_control_plane.intent_engine import aurora_intent_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuroraDevServer:
    """Development server for Aurora OS"""
    
    def __init__(self):
        self.mcp_host = aurora_mcp_host
        self.intent_engine = aurora_intent_engine
    
    async def start(self):
        """Start development server"""
        logger.info("Starting Aurora OS Development Server...")
        
        # Start MCP host
        await self.mcp_host.start()
        
        # Start intent engine
        await self.intent_engine.start()
        
        logger.info("Development server started successfully!")
        logger.info("Commands available:")
        logger.info("  'help' - Show available commands")
        logger.info("  'status' - Show system status")
        logger.info("  'test <input>' - Test intent engine")
        logger.info("  'context <type>' - Request context")
        logger.info("  'quit' - Stop server")
        
        # Interactive mode
        await self.interactive_mode()
    
    async def interactive_mode(self):
        """Interactive command mode"""
        while True:
            try:
                command = input("\naurora-dev> ").strip()
                
                if command == 'quit':
                    break
                elif command == 'help':
                    self.show_help()
                elif command == 'status':
                    await self.show_status()
                elif command.startswith('test '):
                    test_input = command[5:]
                    await self.test_intent_engine(test_input)
                elif command.startswith('context '):
                    context_type = command[8:]
                    await self.test_mcp_context(context_type)
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        await self.stop()
    
    def show_help(self):
        """Show help information"""
        print("\nAvailable Commands:")
        print("  help                    - Show this help")
        print("  status                  - Show system status")
        print("  test <input>            - Test intent engine")
        print("  context <type>          - Request context (system, filesystem, security)")
        print("  quit                    - Stop development server")
    
    async def show_status(self):
        """Show system status"""
        print("\n=== Aurora OS Development Server Status ===")
        
        # MCP Host status
        mcp_health = await self.mcp_host.health_check()
        print(f"MCP Host: {'✓ Running' if mcp_health['host_started'] else '✗ Stopped'}")
        print(f"  Providers: {mcp_health['provider_count']}")
        
        # Intent engine metrics
        intent_metrics = aurora_intent_engine.get_metrics()
        print(f"Intent Engine: ✓ Running")
        print(f"  Processed: {intent_metrics['total_processed']} intents")
        print(f"  Success Rate: {(intent_metrics['successful_classifications']/intent_metrics['total_processed']*100):.1f}%")
        print(f"  Avg Confidence: {intent_metrics['average_confidence']:.2f}")
    
    async def test_intent_engine(self, user_input: str):
        """Test intent engine"""
        print(f"\nTesting intent engine with: '{user_input}'")
        
        try:
            intent = await aurora_intent_engine.process_intent(user_input)
            
            print(f"Intent Type: {intent.intent_type.value}")
            print(f"Action Type: {intent.action_type.value}")
            print(f"Primary Action: {intent.primary_action}")
            print(f"Confidence: {intent.confidence:.2f}")
            print(f"Entities: {len(intent.entities)} found")
            
            for entity in intent.entities:
                print(f"  - {entity.entity_type}: {entity.value} (confidence: {entity.confidence:.2f})")
                
        except Exception as e:
            print(f"Error processing intent: {e}")
    
    async def test_mcp_context(self, context_type: str):
        """Test MCP context request"""
        print(f"\nTesting MCP context request for: {context_type}")
        
        try:
            from mcp.system.mcp_host import MCPRequest, ContextType
            
            # Create test request
            context_types = []
            if context_type.lower() == 'system':
                context_types.append(ContextType.SYSTEM)
            elif context_type.lower() == 'filesystem':
                context_types.append(ContextType.FILESYSTEM)
            elif context_type.lower() == 'security':
                context_types.append(ContextType.SECURITY)
            else:
                print(f"Unknown context type: {context_type}")
                return
            
            request = MCPRequest(
                request_id="test-" + str(int(time.time())),
                consumer_id="dev-server",
                context_types=context_types,
                permissions=[]
            )
            
            # Register consumer
            aurora_mcp_host.register_consumer("dev-server", "system")
            
            # Request context
            response = await aurora_mcp_host.request_context(request)
            
            if response.success:
                print(f"Received {len(response.contexts)} contexts:")
                for context in response.contexts:
                    print(f"  - {context.context_type.value}: {len(context.data)} data points")
            else:
                print(f"Error: {response.error}")
                
        except Exception as e:
            print(f"Error requesting context: {e}")
    
    async def stop(self):
        """Stop development server"""
        logger.info("Stopping Aurora OS Development Server...")
        
        await self.mcp_host.stop()
        await self.intent_engine.stop()
        
        logger.info("Development server stopped")

if __name__ == "__main__":
    import time
    
    server = AuroraDevServer()
    asyncio.run(server.start())
EOF

chmod +x tools/dev_server.py
print_success "Development server created"

# Create configuration files
print_status "Creating configuration files..."

# Create Aurora OS configuration
cat > config/aurora_config.json << 'EOF'
{
  "version": "1.0.0",
  "build": {
    "kernel_version": "6.1",
    "target_architecture": "x86_64",
    "optimization_level": "release"
  },
  "ai": {
    "models_path": "models/",
    "confidence_threshold": 0.7,
    "max_context_age": 300,
    "learning_enabled": true
  },
  "mcp": {
    "default_providers": ["system", "filesystem", "security"],
    "context_timeout": 30.0,
    "max_contexts_per_request": 100
  },
  "security": {
    "zero_trust_enabled": true,
    "encryption_enabled": true,
    "audit_logging": true
  },
  "desktop": {
    "default_shell": "aurora",
    "theme": "dark",
    "animations_enabled": true
  },
  "logging": {
    "level": "INFO",
    "file": "logs/aurora.log",
    "max_size": "10MB",
    "backup_count": 5
  }
}
EOF

# Create development configuration
cat > config/dev_config.json << 'EOF'
{
  "development": {
    "debug_enabled": true,
    "verbose_logging": true,
    "hot_reload": true,
    "test_mode": true
  },
  "testing": {
    "mock_external_services": true,
    "use_test_data": true,
    "parallel_execution": true
  },
  "profiling": {
    "enabled": true,
    "output_dir": "profiles/",
    "cpu_profiling": true,
    "memory_profiling": true
  }
}
EOF

print_success "Configuration files created"

# Set up testing framework
print_status "Setting up testing framework..."

# Create pytest configuration
cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    kernel: Kernel tests
    ai: AI tests
    mcp: MCP tests
    security: Security tests
    performance: Performance tests
EOF

# Create test configuration
cat > tests/conftest.py << 'EOF'
"""
Pytest configuration for Aurora OS tests
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add Aurora OS to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mcp_host():
    """Provide MCP host instance for tests"""
    from mcp.system.mcp_host import MCPHost
    
    host = MCPHost()
    await host.start()
    
    # Register test consumer
    host.register_consumer("test-consumer", "system")
    
    yield host
    
    await host.stop()

@pytest.fixture
async def intent_engine():
    """Provide intent engine instance for tests"""
    from system.ai_control_plane.intent_engine import IntentEngine
    
    engine = IntentEngine()
    await engine.start()
    
    yield engine
    
    await engine.stop()
EOF

print_success "Testing framework configured"

# Create documentation structure
print_status "Setting up documentation structure..."

mkdir -p docs/{api,user,developer,architecture}

# Create Sphinx configuration
cat > docs/conf.py << 'EOF'
project = 'Aurora OS'
copyright = '2024, Aurora OS Team'
author = 'Aurora OS Team'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
}
EOF

print_success "Documentation structure created"

# Set up CI/CD configuration
print_status "Setting up CI/CD configuration..."

mkdir -p .github/workflows

# Create GitHub Actions workflow
cat > .github/workflows/ci.yml << 'EOF'
name: Aurora OS CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y build-essential linux-headers-generic
        pip install -r requirements.txt
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Format check with black
      run: |
        black --check .
    
    - name: Run tests
      run: |
        make test
    
    - name: Build kernel modules
      run: |
        make build-kernel
    
    - name: Build system components
      run: |
        make build-system
        make build-ai
        make build-mcp

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run security audit
      run: |
        make security-audit
EOF

print_success "CI/CD configuration created"

# Final setup
print_status "Completing setup..."

# Create activation reminder
cat > SETUP_COMPLETE.txt << 'EOF'
Aurora OS Development Environment Setup Complete!

Next steps:
1. Activate the environment:
   source activate_aurora.sh

2. Start the development server:
   python tools/dev_server.py

3. Build the system:
   make build

4. Run tests:
   make test

5. View documentation:
   make docs

For more information, see the README.md file.
EOF

print_success "Setup completed successfully!"

echo ""
echo -e "${GREEN}🎉 Aurora OS development environment is ready!${NC}"
echo ""
echo "To start developing:"
echo "1. Activate the environment: source activate_aurora.sh"
echo "2. Start development server: python tools/dev_server.py"
echo "3. Build the system: make build"
echo "4. Run tests: make test"
echo ""
echo "Happy coding! 🚀"