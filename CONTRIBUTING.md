# Contributing to V.A.P.E

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/V.A.P.E.git`
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Install dependencies: `npm install`

## Development Setup

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Run tests
npm test

# Start development mode
npm run dev
```

## Code Style

- Use ES6+ syntax
- Follow JSDoc conventions for functions
- 2-space indentation
- Descriptive variable names
- Comments for complex logic

## Module Guidelines

Each module should:
- Have a clear, single responsibility
- Export a class or function
- Include JSDoc comments
- Log key operations
- Handle errors gracefully

Example:

```javascript
/**
 * MyModule Description
 * 
 * Responsibilities:
 * - Task 1
 * - Task 2
 */
class MyModule {
  constructor(dependencies) {
    this.name = 'MyModule';
    // Initialize
  }

  /**
   * Public method description
   */
  async publicMethod() {
    try {
      logger.info('Executing public method...');
      // Implementation
      return result;
    } catch (error) {
      logger.error('Failed:', error.message);
      throw error;
    }
  }
}

export default MyModule;
```

## Testing

```bash
# Run all tests
npm test

# Run specific test
npm test -- tests/core.test.js

# Run with coverage
npm test -- --coverage
```

Test guidelines:
- Write tests for new features
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies

Example:

```javascript
import { describe, it } from 'node:test';
import assert from 'node:assert';

describe('MyFeature', () => {
  it('should do something', () => {
    // Arrange
    const input = 'test';
    
    // Act
    const result = doSomething(input);
    
    // Assert
    assert.strictEqual(result, 'expected');
  });
});
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Run `npm test` to ensure all tests pass
4. Run `npm run lint` to check code style
5. Create descriptive commit messages
6. Submit PR with description of changes

### Commit Messages

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring

Example:
```
feat: Add new vulnerability signature detection

- Implement reentrancy vulnerability detection
- Add test cases
- Update documentation
```

## Code Review

PRs will be reviewed for:
- Code quality and style
- Test coverage
- Documentation completeness
- Performance implications
- Security considerations

## Issues

### Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Node version, etc.)
- Error logs if available

### Feature Requests

Include:
- Clear description of feature
- Use case / motivation
- Proposed implementation (if any)
- Alternatives considered

## Documentation

Update relevant docs for:
- New modules
- Configuration changes
- New features
- Bug fixes (if user-facing)

Documentation files:
- `README.md` - Project overview
- `docs/DEPLOYMENT.md` - Deployment guide
- `docs/ARCHITECTURE.md` - Technical architecture
- `docs/ACP_PROTOCOL.md` - Protocol integration
- Module comments - Inline code documentation

## Security

- Never commit `.env` files
- Don't hardcode API keys or secrets
- Validate external input
- Keep dependencies updated
- Report security issues privately

## Performance

- Profile before optimizing
- Avoid blocking operations
- Use caching strategically
- Monitor memory usage
- Test with large datasets

## Release Process

1. Update version in `package.json`
2. Update `CHANGELOG.md` (if exists)
3. Tag release: `git tag v1.0.0`
4. Push: `git push origin --tags`

## Questions?

- Check existing issues and discussions
- Review documentation
- Open a new issue for discussion
- Contact maintainers

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn
- Respect privacy and security

Thank you for contributing! 🦍
