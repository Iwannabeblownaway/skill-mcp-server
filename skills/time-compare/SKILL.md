---
name: time-compare
description: Compare local system time with remote server time from sorftime. Use when user needs to verify time synchronization, check time offset between local and remote servers, or diagnose time-related issues. Triggers when user mentions "time compare", "check time sync", "verify system time", or "time offset".
mcp_config:
  sorftime:
    url: https://mcp.sorftime.com?key=your-key-here
---

# Time Compare Skill

Compare local system time with remote sorftime server time to check for time drift or synchronization issues.

## Usage

When user wants to compare times:

1. Get local current time: `date` or `Get-Date` command
2. Call sorftime MCP service to get remote server time using `sorftime_get_time` tool
3. Calculate and display the difference

### Step-by-Step

1. **Get local time**:
   - Windows: `(Get-Date).ToString("yyyy-MM-dd HH:mm:ss")`
   - Linux/Mac: `date "+%Y-%m-%d %H:%M:%S"`

2. **Get remote time** from sorftime MCP:
   - Use `sorftime_get_time` tool (no parameters needed)

3. **Compare and report**:
   - Calculate offset = remote_time - local_time
   - Display in seconds with sign (+/-)
   - Report status based on threshold

### Example Output

```
=== Time Comparison Report ===

Local Time:  2026-04-17 15:30:25 (UTC+8)
Remote Time: 2026-04-17 15:30:28 (UTC+8)
Offset:      +3 seconds

Status: ✓ Time synchronized (offset < 5 seconds)
```

## MCP Tool Reference

This skill uses the `sorftime` MCP service:
- `sorftime_get_time` - Get current server time from sorftime

## Notes

- Positive offset: remote time is ahead of local time
- Negative offset: remote time is behind local time
- Threshold for "synchronized": < 5 seconds (configurable)
