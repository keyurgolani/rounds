"""Unix Find Command — Medium. Logical & Maintainable / Strategy Pattern.

Implement an extensible `find` API. The win isn't a clever algorithm —
it's a clean abstraction. FileMatcher interface + recursive walk +
AND/OR composers turns 'find files > 5MB' and 'find XML files' into
two-line callsites with a shared engine."""
from builder.registry import register


PAYLOAD = {
    "title": "Unix Find Command (Composable Matchers)",
    "difficulty": "Medium",
    "description": (
        "Implement a flexible `find` API that walks a virtual file tree and returns matching paths. The "
        "design must accommodate at least these two use cases without a rewrite:\n"
        "1. Find every file larger than 5 MB under a directory.\n"
        "2. Find every file with extension `.xml` under a directory.\n\n"
        "And, at the next level: 'find PDFs modified less than 2 days ago' should be one more line, not "
        "another rewrite.\n\n"
        "**Test framing:** the file system is encoded as a flat list of `(path, size, ext, mtime)` tuples. "
        "Your function `find(files, matcher)` returns the list of paths whose entries pass the matcher. "
        "Matchers are composable: provide combinators `AND(*matchers)` and `OR(*matchers)`.\n\n"
        "**Example:**\n"
        "```\n"
        "files = [('a.xml', 1, 'xml', 0), ('big.bin', 6_000_000, 'bin', 0)]\n"
        "find(files, ext_eq('xml'))      # ['a.xml']\n"
        "find(files, size_gt(5_000_000)) # ['big.bin']\n"
        "find(files, OR(ext_eq('xml'), size_gt(5_000_000)))  # ['a.xml', 'big.bin']\n"
        "```"
    ),
    "hints": [
        "Define a `Matcher` interface (a callable taking a file entry and returning bool). Concrete matchers: `ExtensionMatcher`, `SizeMatcher`, `MtimeMatcher`. Composers: `AndMatcher`, `OrMatcher`, `NotMatcher`.",
        "The `find` engine walks the tree and applies the matcher to each entry. Matcher and engine are decoupled — adding a new attribute is just one new matcher class.",
        "Symbolic-link gotcha (real-world): cycles cause infinite loops. Track visited inodes / canonicalised paths.",
        "Concurrency follow-up: parallel directory walks with a shared visited set protected by a lock, OR thread-local sets merged at the end.",
        "Edge cases: empty file list, matcher that matches nothing, deeply nested matchers, OR / AND with no children.",
    ],
    "constraints": [
        "0 <= |files| <= 10⁵",
    ],
    "starter_code": {
        "python": (
            "def ext_eq(ext): pass\n"
            "def size_gt(threshold): pass\n"
            "def and_match(*matchers): pass\n"
            "def or_match(*matchers): pass\n"
            "def find(files, matcher): pass"
        ),
        "javascript": (
            "function extEq(ext) {}\n"
            "function sizeGt(t) {}\n"
            "function andMatch(...m) {}\n"
            "function orMatch(...m) {}\n"
            "function find(files, matcher) {}"
        ),
        "java": (
            "// Define interface FileMatcher { boolean match(FileEntry f); }\n"
            "// Concrete matchers + composers, then a static find().\n"
            "class Solution {\n"
            "    public List<String> find(List<FileEntry> files, FileMatcher m) { return new ArrayList<>(); }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    files = [('a.xml', 1, 'xml', 0), ('big.bin', 6_000_000, 'bin', 0)]\n"
            "    print(find(files, ext_eq('xml')))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"files": [["a.xml", 1, "xml", 0], ["big.bin", 6000000, "bin", 0]],
                    "rule": ["ext", "xml"]},
         "expected": ["a.xml"],
         "description": "ext_eq('xml')", "tags": ["basic"]},
        {"input": {"files": [["a.xml", 1, "xml", 0], ["big.bin", 6000000, "bin", 0]],
                    "rule": ["size_gt", 5000000]},
         "expected": ["big.bin"],
         "description": "size_gt(5_000_000)", "tags": ["basic"]},
        {"input": {"files": [["a.xml", 1, "xml", 0], ["big.bin", 6000000, "bin", 0],
                              ["medium.pdf", 3000000, "pdf", 0]],
                    "rule": ["or", ["ext", "xml"], ["size_gt", 5000000]]},
         "expected": ["a.xml", "big.bin"],
         "description": "OR composition", "tags": ["basic"]},
        {"input": {"files": [["a.xml", 6000000, "xml", 0], ["b.xml", 1, "xml", 0],
                              ["c.bin", 6000000, "bin", 0]],
                    "rule": ["and", ["ext", "xml"], ["size_gt", 5000000]]},
         "expected": ["a.xml"],
         "description": "AND composition", "tags": ["basic"]},
        {"input": {"files": [], "rule": ["ext", "xml"]}, "expected": [],
         "description": "Empty file list", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Strategy Pattern (Function Composition)",
            "time_complexity": "O(N · M) where M = matcher complexity",
            "space_complexity": "O(M) for the matcher tree",
            "description": (
                "Each matcher is a callable `entry → bool`. Concrete matchers: extension, size, mtime. "
                "Composers `AND` and `OR` take a list of children and short-circuit appropriately. The "
                "`find` engine is a single linear walk applying the root matcher to every entry. New "
                "attributes (modification time, owner, permission bits) are one new matcher class away — "
                "no engine change."
            ),
            "code": {
                "python": (
                    "def ext_eq(ext):\n"
                    "    return lambda f: f[2] == ext\n\n"
                    "def size_gt(threshold):\n"
                    "    return lambda f: f[1] > threshold\n\n"
                    "def mtime_after(t):\n"
                    "    return lambda f: f[3] > t\n\n"
                    "def and_match(*matchers):\n"
                    "    return lambda f: all(m(f) for m in matchers)\n\n"
                    "def or_match(*matchers):\n"
                    "    return lambda f: any(m(f) for m in matchers)\n\n"
                    "def not_match(matcher):\n"
                    "    return lambda f: not matcher(f)\n\n"
                    "def find(files, matcher):\n"
                    "    return [f[0] for f in files if matcher(f)]"
                ),
                "javascript": (
                    "const extEq = ext => f => f.ext === ext;\n"
                    "const sizeGt = t => f => f.size > t;\n"
                    "const andMatch = (...ms) => f => ms.every(m => m(f));\n"
                    "const orMatch = (...ms) => f => ms.some(m => m(f));\n"
                    "const find = (files, matcher) => files.filter(matcher).map(f => f.path);"
                ),
                "java": (
                    "interface FileMatcher { boolean match(FileEntry f); }\n"
                    "class ExtMatcher implements FileMatcher {\n"
                    "    private final String ext;\n"
                    "    public ExtMatcher(String e) { this.ext = e; }\n"
                    "    public boolean match(FileEntry f) { return f.ext.equals(ext); }\n"
                    "}\n"
                    "class SizeGtMatcher implements FileMatcher {\n"
                    "    private final long threshold;\n"
                    "    public SizeGtMatcher(long t) { this.threshold = t; }\n"
                    "    public boolean match(FileEntry f) { return f.size > threshold; }\n"
                    "}\n"
                    "class AndMatcher implements FileMatcher {\n"
                    "    private final List<FileMatcher> ms;\n"
                    "    public AndMatcher(FileMatcher... ms) { this.ms = Arrays.asList(ms); }\n"
                    "    public boolean match(FileEntry f) {\n"
                    "        for (FileMatcher m : ms) if (!m.match(f)) return false;\n"
                    "        return true;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Don't write a single mega-method that branches on size, extension, time. That dies under the next requirement.",
        "2. Strategy pattern: each criterion is its own matcher class. Engine takes a single matcher, applies it to every entry.",
        "3. Composers (AND/OR/NOT) build trees of matchers. Same interface, no engine change.",
        "4. The two stated requirements are now two trivial callsites: `find(tree, ext_eq('xml'))` and `find(tree, size_gt(5_000_000))`.",
        "5. Adding 'PDFs modified less than 2 days ago' is `find(tree, and_match(ext_eq('pdf'), mtime_after(now - 2*DAY)))`. One line.",
        "6. Symlink and concurrency follow-ups are about the engine, not the matchers — nice clean separation.",
    ],
    "tips": [
        "If you write a class with 5 if-branches, you've already failed the 'maintainable' rubric. Strategy or chain-of-responsibility from the start.",
        "Composers take varargs / lists, not pairs — generalises to N-way without nesting.",
        "Symbolic links: track canonicalised inodes (NOT path strings) to detect cycles.",
        "Multi-threaded walk: thread-local visited sets merged at the end is usually faster than a shared lock.",
        "Common follow-up: 'add streaming results so callers can iterate as the walk progresses.' Generator/iterator pattern; matcher logic unchanged.",
        "Common follow-up: 'how would you persist the index for repeated queries?' This is where you'd add a database or in-memory secondary index per attribute.",
    ],
    "companies": ["Amazon", "Google", "Microsoft"],
    "topics": ["Strategy Pattern", "Composition", "Recursion", "Design"],
    "time_complexity": "O(N) per query",
    "space_complexity": "O(M) matcher tree",
}


def REFERENCE(files, rule):
    """Test driver: rule is a recursive nested list — ['ext', 'xml'], ['size_gt', N], ['and', r1, r2, …], etc."""

    def compile_rule(r):
        if r[0] == "ext":
            ext = r[1]
            return lambda f: f[2] == ext
        if r[0] == "size_gt":
            t = r[1]
            return lambda f: f[1] > t
        if r[0] == "mtime_after":
            t = r[1]
            return lambda f: f[3] > t
        if r[0] == "and":
            children = [compile_rule(c) for c in r[1:]]
            return lambda f: all(m(f) for m in children)
        if r[0] == "or":
            children = [compile_rule(c) for c in r[1:]]
            return lambda f: any(m(f) for m in children)
        if r[0] == "not":
            child = compile_rule(r[1])
            return lambda f: not child(f)
        raise ValueError(f"Unknown rule kind: {r[0]}")

    matcher = compile_rule(rule)
    return [f[0] for f in files if matcher(f)]


register(PAYLOAD, REFERENCE)
