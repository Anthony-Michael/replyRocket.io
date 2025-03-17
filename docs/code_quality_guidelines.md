# Clean Code Guidelines for ReplyRocket.io

This document outlines the clean code principles applied to the ReplyRocket.io codebase, based on best practices from "Code Complete" and other industry standards. Following these guidelines will help maintain a consistent, readable, and maintainable codebase.

## Function Length and Complexity

- **Keep functions short**: Aim for functions under 20 lines of code.
- **Single Responsibility Principle**: Each function should do one thing and do it well.
- **Extract helper functions**: Break down complex functions into smaller, focused helper functions.
- **Use descriptive function names**: Names should clearly indicate what the function does.

Example:
```python
# Instead of this:
def send_email(recipient, subject, body, ...):
    # 50 lines of code doing multiple things
    
# Do this:
def send_email(recipient, subject, body, ...):
    message = create_email_message(recipient, subject, body)
    return send_smtp_message(message, smtp_config)
```

## Code Duplication

- **DRY (Don't Repeat Yourself)**: Extract common logic into shared utility functions.
- **Create utility modules**: Place shared functionality in dedicated utility modules.
- **Centralize validation logic**: Common validation patterns should be extracted to utility functions.

Example:
```python
# Instead of repeating validation logic:
if campaign.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not enough permissions")
    
# Create a utility function:
def validate_campaign_access(db, campaign_id, user_id):
    # Validation logic here
```

## Naming Conventions

- **Consistent naming style**: Use `snake_case` for variables, functions, and modules.
- **Descriptive names**: Names should clearly indicate purpose and usage.
- **Consistent prefixes**: Use consistent prefixes for similar operations (`get_`, `create_`, `update_`, `delete_`).
- **Avoid abbreviations**: Use full, descriptive names unless abbreviations are universally understood.

Examples:
```python
# Good
def get_user_by_email(email: str) -> User:
    ...

# Bad
def fetch_usr(eml: str) -> User:
    ...
```

## Docstrings and Comments

- **All public functions need docstrings**: Include description, args, returns, and raises.
- **Use consistent docstring format**:
  ```python
  def function_name(param1, param2):
      """
      Short description of what the function does.
      
      Args:
          param1: Description of param1
          param2: Description of param2
          
      Returns:
          Description of return value
          
      Raises:
          ExceptionType: When and why this exception is raised
      """
  ```
- **Comment complex logic**: Explain "why" not "what" the code does.
- **Update docstrings when changing code**: Keep documentation synchronized with implementation.

## Error Handling

- **Be specific with exceptions**: Catch specific exceptions, not broad Exception classes.
- **Provide meaningful error messages**: Error messages should help with troubleshooting.
- **Log errors appropriately**: Use different log levels (debug, info, warning, error) appropriately.
- **Don't swallow exceptions**: Always log or handle exceptions properly.

Example:
```python
try:
    result = db.query(User).filter_by(email=email).first()
    return result
except SQLAlchemyError as e:
    logger.error(f"Database error: {str(e)}")
    raise HTTPException(status_code=500, detail="Database error occurred")
```

## Imports

- **Organize imports by groups**:
  1. Standard library imports
  2. Third-party imports
  3. Application imports
- **Use absolute imports** for application modules.
- **Avoid wildcard imports** (`from module import *`).

Example:
```python
# Standard library imports
import json
from typing import Dict, List, Optional

# Third-party imports
from fastapi import APIRouter, Depends

# Application imports
from app.core.config import settings
from app.api import deps
```

## Endpoint Structure

- **Route handlers should be thin**: Delegate business logic to service functions.
- **Consistent response structure**: Maintain consistent response formats across endpoints.
- **Use dependency injection**: Leverage FastAPI's dependency injection for common dependencies.
- **Structured error responses**: Use consistent error response structure.

Example:
```python
@router.get("/{item_id}", response_model=ItemResponse)
def read_item(
    *,
    db: Session = Depends(deps.get_db),
    item_id: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get an item by ID."""
    # Validate access
    item = validate_item_access(db, item_id, current_user.id)
    # Return response
    return item
```

## Testing

- **Write tests for all functionality**: Aim for high test coverage.
- **Use the Arrange-Act-Assert pattern**: Structure tests clearly.
- **Test error cases**: Test both success and failure scenarios.
- **Mock external dependencies**: Use mocks for external services.
- **Use descriptive test names**: Names should describe the scenario being tested.

Example:
```python
def test_user_registration_with_existing_email():
    """Test that registration fails when email already exists."""
    # Arrange
    existing_email = "existing@example.com"
    # Create user with this email...
    
    # Act
    response = client.post("/register", json={"email": existing_email, ...})
    
    # Assert
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
```

## Summary

By following these guidelines, we ensure that our codebase remains maintainable, readable, and robust. These principles help new team members understand the code more quickly and reduce the likelihood of introducing bugs during development.

Remember that clean code is a continuous effort, and code reviews should enforce these standards to maintain code quality over time. 