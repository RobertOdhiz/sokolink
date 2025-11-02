# Contributing to Sokolink Advisor

Thank you for your interest in contributing to Sokolink Advisor! We welcome contributions from the community and are grateful for your support.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- **Clear title**: Brief description of the bug
- **Description**: Detailed explanation of the issue
- **Steps to reproduce**: How to trigger the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: Python version, OS, dependencies
- **Screenshots/logs**: If applicable

### Suggesting Features

We welcome feature suggestions! Please create an issue with:
- **Use case**: Why this feature would be valuable
- **Detailed description**: What the feature should do
- **Potential implementation**: If you have ideas on how to implement it
- **Related issues**: Links to similar feature requests

### Code Contributions

#### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/sokolink.git
   cd sokolink
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate
   # Linux/Mac: source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` File**
   ```bash
   cp env.example .env
   # Edit .env with your test credentials
   ```

#### Development Workflow

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make Changes**
   - Write clean, readable code
   - Follow Python PEP 8 style guidelines
   - Add comments for complex logic
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run the application
   python -m uvicorn app.main:app --reload
   
   # Test endpoints
   curl http://localhost:8000/health
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```
   
   **Commit Message Guidelines:**
   - Use clear, descriptive messages
   - Start with a verb (e.g., "Add", "Fix", "Update")
   - Reference issue numbers if applicable (e.g., "Fix #123: WhatsApp message formatting")

5. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a Pull Request on GitHub with:
   - Clear title and description
   - Link to related issues
   - Screenshots if UI changes
   - Test results if applicable

## 📝 Code Style Guidelines

### Python Style

- Follow **PEP 8** style guide
- Use **type hints** for function parameters and returns
- Keep functions focused and small
- Use meaningful variable and function names
- Add docstrings for classes and functions

### Example:
```python
async def process_compliance_request(
    user_message: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a compliance request from a user.
    
    Args:
        user_message: The user's business inquiry
        session_id: Optional session identifier
        
    Returns:
        Dictionary containing compliance roadmap
    """
    # Implementation here
    pass
```

### File Structure

- Keep related code in appropriate modules
- Services in `app/services/`
- Routes in `app/routes/`
- Models in `app/models/`
- Utilities in `app/utils/`

### Logging

- Use `structlog` for structured logging
- Include relevant context in log messages
- Use appropriate log levels:
  - `debug`: Detailed diagnostic information
  - `info`: General informational messages
  - `warning`: Warning messages
  - `error`: Error messages

Example:
```python
logger.info(
    "Processing compliance request",
    session_id=session_id,
    user_message_length=len(user_message)
)
```

## 🔍 Code Review Process

1. **Pull Request Review**
   - All PRs require at least one approval
   - Maintainers will review for code quality, tests, and documentation
   - Address feedback promptly

2. **Changes Requested**
   - If changes are requested, update your PR
   - Respond to comments and questions
   - Mark conversations as resolved when done

3. **Merge Process**
   - Once approved, maintainers will merge your PR
   - Squash and merge is preferred for cleaner history

## 🧪 Testing

When contributing, please ensure:

- Your code doesn't break existing functionality
- New features include appropriate error handling
- Edge cases are considered
- Performance implications are reasonable

### Manual Testing Checklist

- [ ] Application starts without errors
- [ ] Health endpoint responds correctly
- [ ] WhatsApp webhook handlers work
- [ ] Watsonx service integration works
- [ ] Error handling works as expected
- [ ] Logging is appropriate

## 📚 Documentation

When contributing, please update:

- **README.md**: If adding new features or changing setup
- **Code comments**: For complex logic or algorithms
- **Docstrings**: For new functions and classes
- **This file**: If contributing guidelines change

## 🚫 What NOT to Include

- **API Keys or Secrets**: Never commit credentials
- **Large binary files**: Use Git LFS if necessary
- **Personal information**: Remove any personal data
- **Unnecessary dependencies**: Only add what's needed

## 🎯 Priority Areas for Contribution

We especially welcome contributions in:

1. **Agent Improvements**: Better prompts and agent configurations
2. **Workflow Enhancements**: Optimizing the compliance workflow
3. **Error Handling**: More robust error recovery
4. **Testing**: Unit tests and integration tests
5. **Documentation**: Improving guides and examples
6. **Performance**: Optimizing response times
7. **Features**: New compliance guidance features

## 💬 Communication

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Report security issues privately to maintainers

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions help make Sokolink Advisor better for Kenyan entrepreneurs. We appreciate your time and effort!

---

**Questions?** Open an issue or reach out to the maintainers.

