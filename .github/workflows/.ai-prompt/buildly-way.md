# The Buildly Way

## Development Philosophy

### Code Organization
- **Backend**: Modular FastAPI routers in `app/` directory
- **Frontend**: Jinja2 templates in `templates/` directory
- **Documentation**: All developer docs in `devdocs/` folder
- **Tests**: Simple regression tests in `tests/` folder

### Documentation Standards

1. **Keep Root Clean**: Only keep essential docs in root (README.md, 00_START_HERE.md)
2. **Developer Docs**: All technical documentation goes in `devdocs/`
3. **AI Context**: Store project memory and patterns in `.ai-prompt/`
4. **Summary Documents**: Only create summary/recap documents at the end of major features or end of day, not after every change

### Testing Approach

**Simple Page-Level Regression Tests**
- Test that pages load without errors (HTTP 200 or expected redirects)
- Don't test business logic in page tests
- Fast, simple, and catches breaking changes
- Run as part of CI/CD pipeline

**Test Structure**:
```python
def test_page_loads():
    """Test that the page loads without error"""
    response = client.get("/endpoint")
    assert response.status_code in [200, 302]  # 302 for auth redirects
```

### Code Patterns

**FastAPI Routes**:
- Use async/await for all route handlers
- Check authentication first
- Handle API errors with try/except
- Return appropriate redirects or templates

**API Integration**:
- Use defensive response handling (paginated, list, direct object)
- Provide fallback data on errors
- Log errors for debugging

**Templates**:
- Extend base.html
- Use Tailwind CSS for styling
- Responsive design by default
- Handle empty states gracefully

**Session Management**:
- Store minimal data in session (user ID, org, product, token)
- Use SessionContext helper methods
- Encrypt session cookies

### File Structure

```
buildly-htmx-frontend/
├── .ai-prompt/           # AI context and memory
│   ├── buildly-way.md    # Development philosophy
│   └── project-context.md # Current project state
├── app/                  # Backend code
│   ├── main.py           # App setup and router registration
│   ├── auth.py           # Authentication routes
│   ├── session.py        # Session management
│   ├── api_client.py     # Buildly API client
│   └── *.py              # Feature routers
├── templates/            # Frontend templates
│   ├── base.html         # Base template
│   └── */                # Feature templates
├── tests/                # Regression tests
│   ├── test_pages.py     # Page load tests
│   └── conftest.py       # Test configuration
├── devdocs/              # Developer documentation
│   └── *.md              # Technical guides
├── README.md             # Project overview
└── 00_START_HERE.md      # Quick start guide
```

### Development Workflow

1. **Feature Development**:
   - Create router in `app/`
   - Create templates in `templates/`
   - Register router in `main.py`
   - Add page test in `tests/`
   - Document in `devdocs/`
   - Always check the API to ensure endpoints are there and develop to the end points https://labs-api.buildly.io/docs/?format%3Dopenapi

Summarizing conversation history...

2. **Testing**:
   - Run regression tests: `pytest tests/`
   - Manual testing in browser
   - Check server logs for errors

3. **Documentation**:
   - Update relevant docs in `devdocs/`
   - Keep docs concise and actionable
   - Include code examples

### API Integration Best Practices

**Buildly Labs API**:
- Base URL: `https://labs-api.buildly.io/`
- Authentication: Bearer token in headers
- Response formats: Handle paginated, list, and direct object responses

**Error Handling**:
```python
try:
    response = await api_client.get(endpoint)
    data = response.get("results", response) if isinstance(response, dict) else response
except Exception as e:
    logger.error(f"API error: {e}")
    data = []  # Fallback
```

### UI/UX Guidelines

- **Mobile First**: Design for mobile, enhance for desktop
- **Progressive Enhancement**: Works without JavaScript
- **HTMX**: Use for dynamic interactions
- **Tailwind CSS**: Use utility classes
- **Icons**: Use emoji or SVG icons
- **Colors**: Consistent color scheme (blue for features, red for issues, yellow for tasks)

### Security Practices

- ✅ Authentication checks on all protected routes
- ✅ Session-based security with encrypted cookies
- ✅ Organization/product filtering in queries
- ✅ No exposed credentials or secrets
- ✅ Input validation on forms
- ✅ CSRF protection via session middleware

### Performance Considerations

- Async API calls for better performance
- Minimize JavaScript for faster page loads
- Use CDN for CSS/JS libraries
- Cache session data appropriately
- Efficient Jinja2 templating

### Code Quality Standards

- No syntax errors
- Proper async/await usage
- Comprehensive error handling
- Clear variable names
- Comments for complex logic
- Consistent code style
