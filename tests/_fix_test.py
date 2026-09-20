filepath = "E:/Simple Projects/A Cafe Finder - Tales to tell when we drink caffeine/tests/test_history.py"
content = open(filepath, "r", encoding="utf-8").read()
lines = content.split("\n")

# The file has duplicate content:
# Lines 0-910: Original content up to the first "if __name__"
# Lines 911-1822: Duplicate of original content (including if __name__ block)
# Lines 1823-2093: Our new TestAdversarialReliability class

# We need to keep lines 0-910 and lines 1823-2093
# But line 910 is empty, so we want lines 0-909 (original content) + lines 1823-2093

# Actually, let's keep lines 0-909 (original content without if __name__)
# and then lines 1823-2093 (our new tests + if __name__)

keep_lines = lines[:909] + lines[1823:]
new_content = "\n".join(keep_lines)

# Make sure it ends with a newline
if not new_content.endswith("\n"):
    new_content += "\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Fixed. New line count: {len(keep_lines)}")
print(f"Last 5 lines:")
for line in keep_lines[-5:]:
    print(f"  {line[:80]}")
