#!/usr/bin/env python3
import requests
import time

BASE_URL = "https://uploade.org"
API_KEY = "up_j6UFECmfhHWJrbJLRf07MT33C_nSmI0TU5AkzLiwkLQ"

LEARNINGS = [
    {"category": "python", "title": "Use enumerate instead of range and len", "content": "Problem: Writing for i in range(len(items)) is verbose and unpythonic.\nCause: Coming from other languages like C or Java.\nSolution: Use enumerate() for index and value simultaneously.\nCode: for i, item in enumerate(items): print(i, item)\nResult: Cleaner, more readable, more Pythonic code.", "tags": ["loops", "clean-code"], "type": "tip"},
    {"category": "python", "title": "String join is faster than concatenation", "content": "Problem: Slow string building in loops using plus operator.\nCause: Strings are immutable, plus creates new objects each time.\nSolution: Collect parts in list, then join at the end.\nCode: result = ''.join(parts) instead of s += part in loop\nResult: O(n) instead of O(n squared) time complexity.", "tags": ["strings", "optimization"], "type": "tip"},
    {"category": "python", "title": "Use zip to iterate multiple sequences together", "content": "Problem: Accessing multiple lists by index is verbose and error-prone.\nCause: Using range(len()) and manual indexing.\nSolution: Use zip() to pair up elements from multiple sequences.\nCode: for name, score in zip(names, scores): print(name, score)\nResult: Cleaner iteration, automatically stops at shortest sequence.", "tags": ["loops", "clean-code"], "type": "tip"},
    {"category": "python", "title": "Dict get method avoids KeyError exceptions", "content": "Problem: KeyError exception when dictionary key might not exist.\nCause: Direct dict[key] access without checking key existence first.\nSolution: Use dict.get(key, default) method for safe access.\nCode: value = config.get('timeout', 30)\nResult: No exception thrown, clean default value handling.", "tags": ["dicts", "errors"], "type": "tip"},
    {"category": "python", "title": "Use any and all for boolean sequence checks", "content": "Problem: Verbose loops to check conditions on sequences.\nCause: Manual iteration with flag variables and early breaks.\nSolution: Use any() or all() built-in functions.\nCode: if any(x > 100 for x in values): handle_large()\nResult: More readable, short-circuits on first match.", "tags": ["loops", "clean-code"], "type": "tip"},
    {"category": "javascript", "title": "Array destructuring for cleaner variable assignment", "content": "Problem: Verbose code extracting values from arrays by index.\nCause: Using array[0], array[1] etc for each value.\nSolution: Use array destructuring for direct assignment.\nCode: const [first, second, ...rest] = myArray\nResult: Cleaner code, works with function returns too.", "tags": ["arrays", "clean-code"], "type": "tip"},
    {"category": "javascript", "title": "Object destructuring in function parameters", "content": "Problem: Functions with many parameters are hard to call correctly.\nCause: Positional arguments require remembering order.\nSolution: Use object parameter with destructuring.\nCode: function createUser({ name, age, email }) { }\nResult: Named parameters, optional with defaults, self-documenting.", "tags": ["functions", "clean-code"], "type": "tip"},
    {"category": "javascript", "title": "Use Array find instead of filter for single item", "content": "Problem: Using filter when you only need first matching element.\nCause: Habit of using filter for all searches.\nSolution: Use find() which returns first match and stops.\nCode: const user = users.find(u => u.id === targetId)\nResult: More efficient, clearer intent, returns item not array.", "tags": ["arrays", "optimization"], "type": "tip"},
    {"category": "javascript", "title": "Nullish assignment operator for defaults", "content": "Problem: Setting default values only when null or undefined.\nCause: Using if statements or ternary operators.\nSolution: Use nullish assignment operator for concise defaults.\nCode: user.name ??= 'Anonymous'\nResult: Only assigns if currently null or undefined.", "tags": ["null-checks", "clean-code"], "type": "tip"},
    {"category": "api", "title": "Always include correlation ID in API responses", "content": "Problem: Cannot trace issues reported by API consumers.\nCause: No shared identifier between request and response.\nSolution: Generate unique ID, return in response header.\nCode: X-Correlation-ID: uuid in both request and response\nResult: Easy debugging, can trace through entire system.", "tags": ["http", "tracing"], "type": "tip"},
    {"category": "api", "title": "Use ETags for cache validation and bandwidth", "content": "Problem: Downloading unchanged resources wastes bandwidth.\nCause: No mechanism to check if resource has changed.\nSolution: Return ETag header, accept If-None-Match.\nCode: If-None-Match: abc123 returns 304 if unchanged\nResult: Significant bandwidth savings on repeated requests.", "tags": ["http", "optimization"], "type": "tip"},
    {"category": "api", "title": "Compress API responses with gzip encoding", "content": "Problem: Large JSON responses slow down API performance.\nCause: Sending uncompressed data over network.\nSolution: Enable gzip compression on server responses.\nCode: Accept-Encoding: gzip, Content-Encoding: gzip\nResult: 70-90% smaller response sizes, faster transfers.", "tags": ["http", "optimization"], "type": "tip"},
    {"category": "database", "title": "Use database connection health checks", "content": "Problem: Stale connections in pool cause query failures.\nCause: Connections timeout but pool thinks they are valid.\nSolution: Configure connection validation on borrow.\nCode: Set validationQuery or testOnBorrow in pool config\nResult: Bad connections detected before queries fail.", "tags": ["sql", "connections"], "type": "tip"},
    {"category": "database", "title": "Limit query results to prevent memory issues", "content": "Problem: Query returns millions of rows crashes application.\nCause: No LIMIT clause on SELECT statements.\nSolution: Always paginate and limit result sets.\nCode: SELECT * FROM items LIMIT 100 OFFSET 0\nResult: Consistent memory usage and response times.", "tags": ["sql", "memory"], "type": "warning"},
    {"category": "database", "title": "Use EXISTS instead of COUNT for checking records", "content": "Problem: COUNT query scans entire table just to check existence.\nCause: Using COUNT(*) > 0 pattern for existence checks.\nSolution: Use EXISTS which stops at first match.\nCode: SELECT EXISTS(SELECT 1 FROM users WHERE email = ?)\nResult: Much faster for large tables, stops early.", "tags": ["sql", "optimization"], "type": "tip"},
    {"category": "devops", "title": "Always pin dependency versions in production", "content": "Problem: Build breaks because dependency released breaking change.\nCause: Using latest or unpinned version specifiers.\nSolution: Pin exact versions in requirements or package.json.\nCode: requests==2.28.1 not requests>=2.0\nResult: Reproducible builds, controlled upgrades.", "tags": ["dependency-management", "docker"], "type": "warning"},
    {"category": "devops", "title": "Use Docker layer caching for faster builds", "content": "Problem: Docker builds are slow, reinstalling dependencies every time.\nCause: Copying all files before installing dependencies.\nSolution: Copy dependency files first, install, then copy code.\nCode: COPY requirements.txt . then RUN pip install then COPY . .\nResult: Dependencies cached, only code changes trigger reinstall.", "tags": ["docker", "optimization"], "type": "tip"},
    {"category": "devops", "title": "Set memory limits to prevent container OOM kills", "content": "Problem: Container randomly killed by kernel OOM killer.\nCause: No memory limit set, container uses all available memory.\nSolution: Set appropriate memory limits in container config.\nCode: docker run --memory=512m or Kubernetes limits\nResult: Predictable behavior, graceful handling of memory pressure.", "tags": ["docker", "memory"], "type": "warning"},
    {"category": "security", "title": "Use constant time comparison for secrets", "content": "Problem: Timing attacks can guess secret values character by character.\nCause: Normal string comparison returns early on mismatch.\nSolution: Use constant-time comparison function.\nCode: secrets.compare_digest(a, b) or crypto.timingSafeEqual\nResult: Comparison time independent of where strings differ.", "tags": ["auth", "encryption"], "type": "warning"},
    {"category": "security", "title": "Implement proper CORS headers for API security", "content": "Problem: API accessible from malicious websites via browser.\nCause: Missing or overly permissive CORS configuration.\nSolution: Whitelist specific allowed origins only.\nCode: Access-Control-Allow-Origin: https://myapp.com\nResult: Only trusted sites can make browser requests to API.", "tags": ["http", "cors"], "type": "warning"},
]

uploaded = 0
for l in LEARNINGS:
    try:
        r = requests.post(f"{BASE_URL}/experiences",
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            json=l, timeout=30)
        if r.status_code == 200:
            uploaded += 1
            print(f"[{uploaded}] ✓ {l['title'][:45]}")
        else:
            print(f"[FAIL] {l['title'][:45]} - {r.status_code}: {r.text[:50]}")
    except Exception as e:
        print(f"[ERR] {l['title'][:45]} - {e}")
    time.sleep(0.5)

print(f"\nDone: {uploaded} uploaded")
print("Checking total...")
r = requests.get(f"{BASE_URL}/health")
print(r.json())
