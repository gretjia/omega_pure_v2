#!/usr/bin/env bash
# Temporary debug hook — dump PostToolUse Bash input to file
INPUT=$(cat)
echo "$INPUT" >> /tmp/claude_post_bash_debug.jsonl
exit 0
