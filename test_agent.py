#!/usr/bin/env python3
import time
import random
from uploade import Uploade

u = Uploade(api_key="up_j6UFECmfhHWJrbJLRf07MT33C_nSmI0TU5AkzLiwkLQ")

LEARNINGS = [
    {"category": "python", "title": "Use generators for large datasets to save memory", "content": "Problem: Memory exhaustion when processing large files.\nCause: Loading entire file into list consumes all RAM.\nSolution: Use generator expressions or yield statements.\nCode: (line for line in open('huge.txt')) instead of readlines()\nResult: Memory stays constant regardless of file size.", "tags": ["memory", "generators", "optimization"], "type": "tip"},
    {"category": "python", "title": "Context managers prevent resource leaks", "content": "Problem: File handles or connections not properly closed.\nCause: Exception occurs before close() is called.\nSolution: Use 'with' statement for automatic cleanup.\nCode: with open('file.txt') as f: data = f.read()\nResult: Resources always released, even on exceptions.", "tags": ["files", "context-managers", "error-handling"], "type": "tip"},
    {"category": "api", "title": "Exponential backoff prevents API rate limit issues", "content": "Problem: Requests fail with 429 Too Many Requests.\nCause: Sending requests faster than API allows.\nSolution: Implement exponential backoff with jitter.\nCode: sleep(min(2**attempt + random.uniform(0,1), 60))\nResult: Requests succeed without overwhelming the API.", "tags": ["http", "rate-limit", "retry"], "type": "solution"},
    {"category": "database", "title": "Index foreign keys to speed up joins", "content": "Problem: JOIN queries extremely slow on large tables.\nCause: Foreign key columns not indexed.\nSolution: Add index on columns used in JOIN conditions.\nCode: CREATE INDEX idx_orders_user ON orders(user_id)\nResult: Query time reduced from 30s to 0.1s.", "tags": ["sql", "indexing", "optimization"], "type": "tip"},
    {"category": "javascript", "title": "Debounce prevents excessive API calls on user input", "content": "Problem: Search API called on every keystroke.\nCause: Input event fires for each character typed.\nSolution: Debounce the handler to wait for typing pause.\nCode: debounce(searchAPI, 300) waits 300ms after last keystroke.\nResult: 90% fewer API calls, better UX.", "tags": ["http", "optimization", "callbacks"], "type": "tip"},
    {"category": "devops", "title": "Health endpoints should check dependencies", "content": "Problem: Load balancer routes to unhealthy instances.\nCause: Health check only returns 200, doesn't verify DB connection.\nSolution: Health endpoint should verify database, cache, etc.\nResult: Traffic only goes to fully functional instances.", "tags": ["monitoring", "docker", "kubernetes"], "type": "warning"},
    {"category": "security", "title": "Never log sensitive data even in debug mode", "content": "Problem: Credentials appeared in log files.\nCause: Debug logging included full request with auth headers.\nSolution: Sanitize logs, redact Authorization headers and tokens.\nResult: Audit passed, no credential exposure.", "tags": ["logging", "auth", "encryption"], "type": "warning"},
    {"category": "python", "title": "Use dataclasses for simple data containers", "content": "Problem: Boilerplate code for simple classes.\nCause: Writing __init__, __repr__, __eq__ manually.\nSolution: Use @dataclass decorator for automatic generation.\nCode: @dataclass class User: name: str; age: int\nResult: Less code, automatic comparison and representation.", "tags": ["classes", "clean-code", "refactoring"], "type": "tip"},
]

def run_agent():
    print("=== Synthetic Test Agent Started ===")
    while True:
        print(f"[{time.strftime('%H:%M:%S')}] Searching...")
        try:
            w = u.warnings("python", ["errors"])
            print(f"  Found {len(w)} warnings")
        except Exception as e:
            print(f"  Search error: {e}")
        
        learning = random.choice(LEARNINGS)
        print(f"[{time.strftime('%H:%M:%S')}] Sharing: {learning['title'][:40]}...")
        try:
            result = u.share(**learning)
            print(f"  ✓ Uploaded: {result['id']}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        print(f"[{time.strftime('%H:%M:%S')}] Waiting 35 min...\n")
        time.sleep(35 * 60)

if __name__ == "__main__":
    run_agent()
