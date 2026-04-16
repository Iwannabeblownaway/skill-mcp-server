# Code Review Skill

When reviewing code, follow these steps:

## 1. Style Check
- Verify code follows project conventions
- Check naming conventions (camelCase, PascalCase, snake_case)
- Look for consistent indentation and formatting

## 2. Logic Review
- Check for bugs, edge cases, and correctness
- Verify variable types and null handling
- Look for potential infinite loops or recursion
- Check error handling paths

## 3. Best Practices
- Ensure modern patterns and efficient algorithms
- Look for code smells (duplication, long functions, etc.)
- Check for security vulnerabilities (SQL injection, XSS, etc.)
- Verify proper resource cleanup

## 4. Documentation
- Check for appropriate docstrings/comments
- Verify README or setup instructions exist
- Ensure complex logic is explained

## Output Format

Provide feedback in this structure:

```
## Summary
[Brief overview of findings]

## Issues Found
1. [Severity] [File:Line] - [Description]
   - Suggestion: [How to fix]

## Recommendations
[Any additional improvements]
```

## Severity Levels
- **CRITICAL**: Must fix before merge
- **MAJOR**: Should fix before merge
- **MINOR**: Optional improvement
- **NITPICK**: Style preference
