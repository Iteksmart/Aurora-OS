# Contributing to Aurora OS

Thank you for your interest in contributing to Aurora OS! We welcome contributions from developers, researchers, designers, and enthusiasts who share our vision for an AI-native operating system.

## 🚀 Quick Start for Contributors

### Prerequisites
- Linux development environment (Ubuntu 20.04+ recommended)
- Python 3.8+
- Git
- Basic familiarity with OS development concepts

### Setup Your Development Environment
```bash
# Clone the repository
git clone https://github.com/Iteksmart/Aurora-OS.git
cd Aurora-OS

# Install dependencies
make build-deps

# Run quick tests to verify setup
make test-quick

# Build your first ISO
make build iso
```

## 🤝 How to Contribute

### 1. Find an Issue
- Check [Good First Issues](https://github.com/Iteksmart/Aurora-OS/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- Look for issues labeled `help wanted`
- Browse [Feature Requests](https://github.com/Iteksmart/Aurora-OS/issues?q=is%3Aissue+is%3Aopen+label%3Afeature)

### 2. Create Your Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Your Changes
- Follow our [Code Style Guidelines](#code-style)
- Add tests for your changes
- Update documentation if needed
- Ensure all tests pass: `make tests`

### 4. Submit Your Pull Request
- Push your branch: `git push origin feature/your-feature-name`
- Open a pull request with our [PR Template](#pull-request-template)

## 📝 Issue Templates

### Bug Report Template
```markdown
**Bug Description**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run `make build iso`
2. Execute command '...'
3. See error

**Expected Behavior**
A clear and concise description of what you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Architecture: [e.g. x86_64]
- Aurora OS Version: [e.g. v0.1.0]

**Additional Context**
Add any other context about the problem here.

**Logs/Error Messages**
```
Paste relevant logs here
```
```

### Feature Request Template
```markdown
**Feature Description**
A clear and concise description of the feature you'd like to add.

**Problem Statement**
What problem does this feature solve? What pain point does it address?

**Proposed Solution**
How do you envision this feature working? Include technical details if applicable.

**Alternatives Considered**
What other approaches did you consider? Why did you choose this approach?

**Additional Context**
Add any other context, screenshots, or examples about the feature request.
```

### Good First Issue Template
```markdown
**Task Description**
A clear description of what needs to be done, suitable for new contributors.

**Difficulty Level**
- [ ] Beginner (basic scripting, documentation)
- [ ] Intermediate (familiarity with OS concepts)
- [ ] Advanced (deep technical knowledge required)

**Expected Outcome**
What should be the result when this issue is completed?

**Helpful Resources**
Links to relevant documentation, similar issues, or examples.

**Mentor**
@username who can help with questions

**Time Estimate**
Approximate time expected to complete this task.
```

## 🔧 Pull Request Template

```markdown
## 📋 Description
Brief description of your changes and why they're needed.

## 🎯 Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code cleanup/refactoring

## ✅ Testing
- [ ] I have run `make tests` and all tests pass
- [ ] I have tested my changes manually
- [ ] I have added new tests for my features
- [ ] I have updated documentation if needed

## 📝 Checklist
- [ ] My code follows the [style guidelines](#code-style)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules

## 📸 Screenshots (if applicable)
Add screenshots to help explain your changes.

## 🔗 Related Issues
Fixes #(issue number)
Related to #(issue number)

## 💬 Additional Notes
Any additional context or comments about your changes.
```

## 🎨 Code Style Guidelines

### Python Code
- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black formatter)
- Use type hints where appropriate
- Write docstrings for all functions and classes

### Shell Scripts
- Use 4 spaces for indentation
- Quote variables: `"$VAR"` instead of `$VAR`
- Use `set -euo pipefail` at the top of scripts
- Use meaningful variable names

### Commit Messages
Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

Examples:
```
feat(ai): add intent engine for natural language processing
fix(build): resolve dependency conflict in Makefile
docs(readme): update installation instructions
```

## 🧪 Testing Guidelines

### Running Tests
```bash
# Run all tests
make tests

# Run quick smoke tests
make test-quick

# Run specific test categories
make test-kernel
make test-system
make test-ai
make test-mcp
```

### Writing Tests
- Test files should be in the `tests/` directory
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies when needed
- Keep tests independent and fast

### Test Categories
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interaction between components
- **System Tests**: Test the complete system
- **Performance Tests**: Test performance characteristics

## 📁 Project Structure

```
Aurora-OS/
├── kernel/              # Linux kernel with AI extensions
├── system/              # Aurora system services
├── ai_assistant/        # AI control plane components
├── mcp/                 # MCP nervous system
├── desktop/             # Aurora desktop environment
├── enterprise/          # Enterprise features
├── build/               # Build system and scripts
├── tests/               # Test suites
├── docs/                # Documentation
├── tools/               # Development tools
├── Makefile             # Build system
├── CONTRIBUTING.md      # This file
└── README.md            # Project overview
```

## 🏗️ Development Workflow

### 1. Setup
```bash
git clone https://github.com/Iteksmart/Aurora-OS.git
cd Aurora-OS
make build-deps
```

### 2. Development
```bash
# Create your branch
git checkout -b feature/your-feature

# Make changes
# ... (edit files)

# Test your changes
make test-quick

# Build and test ISO (if applicable)
make build iso
```

### 3. Submit
```bash
# Commit your changes
git add .
git commit -m "feat(component): description of your changes"

# Push and create PR
git push origin feature/your-feature
# Then create a pull request on GitHub
```

## 🎯 Areas of Contribution

### High Priority Areas
1. **AI Control Plane**: Enhance the intent engine and context management
2. **Desktop Environment**: Improve the Aurora Glass UI and widget system
3. **MCP Integration**: Expand the nervous system capabilities
4. **Testing**: Add comprehensive test coverage
5. **Documentation**: Improve guides and API documentation

### Feature Areas
1. **Kernel Extensions**: AI-aware scheduler and resource management
2. **Security**: Zero-trust architecture implementation
3. **Performance**: Optimization and profiling
4. **Enterprise**: Fleet management and compliance features
5. **Accessibility**: Improve accessibility features

### Documentation Areas
1. **User Guides**: End-user documentation
2. **Developer Docs**: API and development guides
3. **Architecture Docs**: System architecture documentation
4. **Tutorials**: Step-by-step tutorials
5. **Examples**: Code examples and use cases

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

### Getting Help
- Join our discussions on GitHub
- Ask questions in issues (use `question` label)
- Check existing documentation first
- Be patient with responses

### Communication
- Use clear, concise language
- Provide context for your questions
- Share relevant code and error messages
- Follow up on your issues and PRs

## 🏆 Recognition

Contributors will be recognized in:
- Our contributors list in README.md
- Release notes for significant contributions
- Special contributor badges (when implemented)
- Potential inclusion in the core team for consistent contributors

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/Iteksmart/Aurora-OS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Iteksmart/Aurora-OS/discussions)
- **Security**: security@aurora-os.org

---

Thank you for contributing to Aurora OS! Your contributions help make the world's first AI-native operating system a reality. 🚀