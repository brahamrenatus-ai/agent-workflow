#!/usr/bin/env python3
"""Facts about a change before anyone reads the diff (agent-workflow, since v3.24).

The agent-workflow skill installs this script as handoff/tools/check_diff.py. It reads the lines a change adds and
compares them with the rest of the code, without any model call. Every mark is a fact to look at, not a verdict: a
name can be a library member the tool does not know, or a doc can describe code on purpose. A bare run
is for the executor: a high- or medium-capacity executor fixes each mark or explains it in the report, and a
low-capacity one copies the mark lines into the report. The head runs it with --docs before reading the diff and
checks each mark in the code; an explanation in a report is a claim, not a clearance.

Marks (one line each: `<CLASS> <name> <file>:<line> | <line text>`):
- UNDEFINED: a name used on a new line that exists nowhere else in the code and is not defined anywhere in the
  change: a property read on repo data, a plain call, `var(--x)` without a definition, a one-word value passed to a
  component (`<Button tone="x">`), an id reference (`htmlFor`, `aria-labelledby`), or a relative import path that
  resolves to no file (TypeScript resolution: .ts/.tsx/.d.ts/index.*);
- UNUSED-IMPORT: a name imported on a new line and never used in that file (`...NAME` spread and JSX tags count);
- DYNAMIC-CALL: a call through a string key, `obj['name'](...)`, on a new line;
- DOC (only with --docs): a name in a code span or code block on a new line of a changed Markdown file that exists
  nowhere in the code. A doc can propose code or describe another system, which a machine cannot tell from a wrong
  claim, so DOC is material for the head, not an obligation for the executor. Without --docs, DOC marks and the doc
  INFO lines are not listed: one line `DOC: N names in changed docs not found in code (run with --docs to list
  them)` gives their count, and they are not in the final count.

Rules that keep marks to outliers:
- Comments, string and template contents, and regex literals are dropped before uses are searched (token scanner
  for JS/TS/JSX/TSX; Python `tokenize`). String contents are read only where a class needs them.
- "Elsewhere in the code" = every text file of the tree in any language (C/C++, SQL, JSON, ...) except documents,
  the agent layer, and the new lines themselves. Names defined on new lines of any file in the change (declarations,
  parameters, object keys, assignments, `id=`/`name=` values, string literals) count as existing, and so do names on
  removed lines.
- Property reads are checked only on repo data: parameters, results of repo functions, and their members. Objects made
  by a global or a package (`new URL()`, `fetch()`, a `react` import, a catch parameter, a method chain ending in a
  method the repo does not define) have library members, and members of the JS/DOM/Node standard library are never
  marked. Calls of language globals and builtins are never marked.
- A Markdown file whose code names are mostly absent from code (a contract written before its code, docs of another
  system) gives one INFO line (with --docs) instead of a mark per name; so does a code block whose names are mostly
  absent (a proposal, code of another system). A `var(--x, fallback)` is optional on purpose and not marked.
- Languages whose uses are not parsed are listed as `not checked: .cpp 3 files`, so nobody assumes coverage.

The agent layer is skipped as in check_process_notes.py (handoff/, agent instruction folders and files, root
NOTES/ROADMAP), except handoff/tools/, where project test tools live. Lockfiles, minified, binary, and > 2 MB files
are skipped.

Usage (from the project root; read-only, every git call runs with --no-optional-locks):
  python handoff/tools/check_diff.py                     # = --worktree: tracked changes vs HEAD + new untracked files
  python handoff/tools/check_diff.py --staged            # staged changes; the tree is the index
  python handoff/tools/check_diff.py --commit <C>        # C against its parent; the tree is C (audit, measuring)
  python handoff/tools/check_diff.py --range A..B        # A..B; the tree is B
  python handoff/tools/check_diff.py --docs              # also list DOC marks and doc INFO lines (head, reviewer)
  python handoff/tools/check_diff.py --json [paths...]   # paths limit the changed files that are checked

When the chosen mode has no changed file to check (after the agent layer and path arguments are left out), the output
says so and names --commit/--range, because a change that is already committed looks clean in --worktree mode.

--json prints {"version": 1, "mode": "worktree"|"staged"|"commit"|"range", "files": N, "marks": [{"class", "name",
"file", "line", "text"}], "info": [...], "not_checked": {".cpp": 3}, "docs_hidden": N}. `files` = changed files with
added lines that were read (unparsed languages included; they are also listed in not_checked); `docs_hidden` = DOC
marks left out because --docs was not given (always 0 with --docs). Exit code: 0 = the check ran (marks are not a
failure), 2 = error.
"""
import argparse
import builtins
import io
import json
import keyword
import os
import posixpath
import re
import subprocess
import sys
import tokenize
from collections import defaultdict

# ---- agent layer and skipped files: same definition as check_process_notes.py, except handoff/tools/ is checked
AGENT_FOLDERS = {".claude", ".agents", ".agent", ".cursor", ".windsurf", ".clinerules"}  # at any depth
AGENT_NAMES = {"claude.md", "claude.local.md", "agents.md", "gemini.md", "conventions.md"}  # file names anywhere
AGENT_ROOT = {"notes.md", "notes_archive.md", "roadmap.md", "skill-feedback.md"}  # files at the root (LITE)
SKIP_FOLDERS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pio", "build", "dist", ".next"}
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock",
             "cargo.lock", "composer.lock", "gemfile.lock", "go.sum", "uv.lock"}
SKIP_SUFFIXES = (".min.js", ".min.css", ".map", ".lock")
MAX_SIZE = 2 * 1024 * 1024
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff", ".psd", ".pdf", ".zip", ".gz",
              ".tgz", ".bz2", ".xz", ".7z", ".rar", ".jar", ".war", ".class", ".so", ".dll", ".exe", ".bin", ".o",
              ".a", ".lib", ".pyc", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".wav", ".ogg", ".webm",
              ".mov", ".avi", ".sqlite", ".db", ".xlsx", ".xls", ".docx", ".pptx", ".skp", ".stl", ".glb", ".hex",
              ".elf", ".dxf"}

JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
JSX_EXT = {".js", ".jsx", ".tsx"}
PY_EXT = {".py", ".pyi"}
CSS_EXT = {".css", ".scss", ".sass", ".less", ".styl"}
HTML_EXT = {".html", ".htm"}
MD_EXT = {".md", ".markdown", ".mdx"}
DOC_EXT = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc"}
PARSED_EXT = JS_EXT | PY_EXT | CSS_EXT | HTML_EXT | MD_EXT
QUIET_EXT = {".txt"}  # prose: no names to check, not listed as "not checked"
RESOLVE_EXT = [".ts", ".tsx", ".d.ts", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".json", ".css", ".scss",
               ".sass", ".less", ".vue", ".svelte", ".node", ".wasm"]
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MAX_PER_CLASS = 25

ID_RE = re.compile(r"[A-Za-z_$][\w$]*")
HYPHEN_RE = re.compile(r"[A-Za-z_][\w]*(?:-[\w]+)+")
WORD_RE = re.compile(r"[A-Za-z][\w-]*")
IDENT_STR = re.compile(r"[A-Za-z_][\w]*(?:-[\w]+)*")
CSSVAR_USE = re.compile(r"var\(\s*(--[\w-]+)\s*([,)])")
CSSVAR_DEF = re.compile(r"(--[\w-]+)['\"]?\s*:|setProperty\(\s*['\"](--[\w-]+)|@property\s+(--[\w-]+)")
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
HTML_ID_ATTR = re.compile(r"\b(?:id|name)\s*=\s*[\"']([^\"'{}$<>\s]+)[\"']")
# DOC names: snake_case with an underscore, or camelCase that starts with two lowercase letters and has a capitalised
# word of two letters or more (`isDuplicate`); units and brands (`mW`, `dBm`, `kVA`, `microSD`) are not names.
DOC_NAME = re.compile(r"(?<![\w$./\\-])([a-z][a-z0-9]*(?:_[a-z0-9]+)+|[a-z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)(?![\w$\\-])")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
QUOTED_VALUE = re.compile(r"([\"'])(?:(?!\1).)*\1(?!\s*:)")
TPL_DECL = re.compile(r"\b(?:const|let|var|function)\s+([A-Za-z_$][\w$]*)|[{,]\s*([A-Za-z_$][\w$]*)\s*(?=[:,}])")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|__mocks__|spec|e2e|fixtures?)/|\.(test|spec)\.[a-z]+$|(^|/)test_[^/]*\.py$|_test\.py$")

JS_KEYWORDS = set("""break case catch class const continue debugger default delete do else enum export extends false
finally for function if import in instanceof new null return super switch this throw true try typeof var void while with
yield let static implements interface package private protected public await async of get set as from undefined NaN
Infinity type satisfies keyof readonly declare namespace module abstract is infer asserts unique override accessor
arguments""".split())
# Reserved words: never names. Contextual words (async, of, get, set, from, as, type) are valid names.
RESERVED = set("""break case catch class const continue debugger default delete do else enum export extends false
finally for function if import in instanceof new null return super switch this throw true try typeof var void while with
yield let static implements interface package private protected public await""".split())
EXPR_KEYWORDS = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else",
                 "yield", "await", "extends"}
# JavaScript, browser, Node, and test-runner globals: calls of these and members of objects made from them are library.
JS_GLOBALS = set("""globalThis Infinity NaN undefined eval isFinite isNaN parseFloat parseInt decodeURI
decodeURIComponent encodeURI encodeURIComponent escape unescape AggregateError Array ArrayBuffer Atomics BigInt
BigInt64Array BigUint64Array Boolean DataView Date Error EvalError FinalizationRegistry Float32Array Float64Array
Function Int8Array Int16Array Int32Array Intl JSON Map Math Number Object Promise Proxy RangeError ReferenceError Reflect
RegExp Set SharedArrayBuffer String Symbol SyntaxError TypeError Uint8Array Uint8ClampedArray Uint16Array Uint32Array
URIError WeakMap WeakRef WeakSet window self document navigator location history screen localStorage sessionStorage
indexedDB console alert confirm prompt fetch setTimeout clearTimeout setInterval clearInterval setImmediate
clearImmediate requestAnimationFrame cancelAnimationFrame requestIdleCallback cancelIdleCallback queueMicrotask
structuredClone atob btoa getComputedStyle matchMedia scrollTo scrollBy open close print postMessage addEventListener
removeEventListener dispatchEvent crypto performance caches URL URLSearchParams Headers Request Response FormData Blob
File FileList FileReader AbortController AbortSignal Event CustomEvent EventTarget EventSource TextEncoder TextDecoder
WebSocket Worker SharedWorker XMLHttpRequest Image Audio Option MutationObserver IntersectionObserver ResizeObserver
PerformanceObserver Notification DOMParser XMLSerializer HTMLElement HTMLInputElement HTMLCanvasElement SVGElement
Element Node NodeList KeyboardEvent MouseEvent PointerEvent TouchEvent BroadcastChannel MessageChannel ReadableStream
WritableStream TransformStream CompressionStream DecompressionStream OffscreenCanvas ImageData Path2D createImageBitmap
CSS ClipboardItem Clipboard WebAssembly process Buffer global module exports require __dirname __filename describe it
test expect beforeEach afterEach beforeAll afterAll vi jest suite context cy Cypress chrome browser Deno Bun
import this super""".split())
# Members of the JavaScript, DOM, and Node standard objects: never marked as fabricated properties.
JS_MEMBERS = set("""length size name message stack code cause errors target currentTarget relatedTarget value
valueAsNumber valueAsDate checked files dataset style key keyCode code charCode which type detail timeStamp clientX
clientY pageX pageY screenX screenY offsetX offsetY movementX movementY deltaX deltaY deltaMode touches changedTouches
targetTouches button buttons altKey ctrlKey metaKey shiftKey repeat isComposing defaultPrevented isTrusted bubbles
cancelable composed current prototype constructor hostname protocol pathname search hash host port origin href
username password searchParams status statusText ok headers body bodyUsed redirected url signal aborted reason result
readyState response responseText responseType responseURL timeout innerHTML outerHTML textContent innerText children
childNodes parentNode parentElement firstChild lastChild firstElementChild lastElementChild nextSibling previousSibling
nextElementSibling previousElementSibling classList className id tagName nodeName nodeType nodeValue attributes
scrollTop scrollLeft scrollHeight scrollWidth clientHeight clientWidth clientTop clientLeft offsetHeight offsetWidth
offsetTop offsetLeft offsetParent width height naturalWidth naturalHeight src alt selected selectedIndex options
selectedOptions disabled placeholder validity validationMessage form labels min max step multiple required readOnly
env argv platform pid ppid arch exitCode versions version execPath meta description data done x y top left right bottom
lastModified lastIndex index input groups flags source global sticky unicode byteLength buffer byteOffset BYTES_PER_ELEMENT
EPSILON MAX_SAFE_INTEGER MIN_SAFE_INTEGER MAX_VALUE MIN_VALUE PI E LN2 LN10 LOG2E LOG10E SQRT2 SQRT1_2 visibilityState
hidden activeElement documentElement head title cookie referrer defaultView devicePixelRatio innerWidth innerHeight
outerWidth outerHeight scrollX scrollY pageXOffset pageYOffset userAgent language languages onLine clipboard
serviceWorker geolocation mediaDevices permissions maxTouchPoints standalone matches media isIntersecting
intersectionRatio boundingClientRect contentRect borderBoxSize entries locale timeZone weekday month day year hour
minute second dateStyle timeStyle storageArea newValue oldValue persisted state length""".split())
# Array/String/Map methods: the value they return is still repo data.
JS_DATA_METHODS = set("""at concat copyWithin entries every fill filter find findIndex findLast findLastIndex flat flatMap
forEach includes indexOf join keys lastIndexOf map pop push reduce reduceRight reverse shift slice some sort splice
toReversed toSorted toSpliced unshift values with charAt trim trimStart trimEnd split substring substr toLowerCase
toUpperCase replace replaceAll padStart padEnd repeat startsWith endsWith normalize get""".split())
ID_REF_ATTRS = {"htmlFor", "for", "aria-labelledby", "aria-describedby", "aria-controls", "aria-owns",
                "aria-activedescendant", "aria-errormessage", "aria-details", "list"}
NO_VALUE_ATTRS = {"className", "class", "style", "key", "ref", "id", "name", "src", "href", "alt", "title", "type",
                  "placeholder", "label", "aria-label", "role", "lang", "dir", "target", "rel", "method", "action",
                  "autoComplete", "inputMode", "enterKeyHint", "loading", "decoding", "fill", "stroke", "d", "viewBox",
                  "xmlns", "as", "to", "path", "element"} | ID_REF_ATTRS
PY_BUILTINS = set(dir(builtins)) | set(keyword.kwlist) | set(getattr(keyword, "softkwlist", [])) | {
    "__file__", "__name__", "__doc__", "__spec__", "__loader__", "__package__", "__builtins__", "__path__",
    "__dict__", "__class__", "reveal_type", "__annotations__"}

LEGEND = {
    "UNDEFINED": "used on a new line, found nowhere else in the code and not defined in this change (could be a "
                 "library member the tool does not know; open the line)",
    "UNUSED-IMPORT": "imported on a new line and not used in that file",
    "DYNAMIC-CALL": "called through a string key; a text search for `.name(` does not find it",
    "DOC": "name in a code span or code block of a changed document that exists nowhere in the code",
}


def setup_output():
    """A Windows console (cp1252) must not crash the script; output to a pipe or an agent is UTF-8."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace") if s.isatty() else s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


class GitError(Exception):
    pass


def git(root, *args, data=None, check=True):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "-c", "core.quotepath=false", *args],
                           input=data, capture_output=True, env=env)
    except OSError as e:
        raise GitError(f"git not found: {e}")
    if check and r.returncode != 0:
        raise GitError(f"git {' '.join(args[:3])}: {r.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return r


def agent_layer(rel):
    parts = [p.lower() for p in rel.replace("\\", "/").split("/") if p and p != "."]
    if not parts:
        return False
    if len(parts) > 1 and parts[0] == "handoff":
        return parts[1] != "tools"
    if len(parts) == 1 and parts[0] in AGENT_ROOT:
        return True
    return any(p in AGENT_FOLDERS for p in parts) or parts[-1] in AGENT_NAMES


def ext_of(rel):
    name = rel.rsplit("/", 1)[-1].lower()
    if name.endswith(".d.ts"):
        return ".ts"
    i = name.rfind(".")
    return name[i:] if i > 0 else ""


def skipped(rel):
    """Not read at all: agent layer, vendored or build folders, lockfiles, minified, known binary extensions."""
    parts = rel.split("/")
    name = parts[-1].lower()
    if agent_layer(rel) or any(p in SKIP_FOLDERS for p in parts[:-1]):
        return True
    return name in LOCKFILES or name.endswith(SKIP_SUFFIXES) or ext_of(rel) in BINARY_EXT


def decode(data):
    if data is None or len(data) > MAX_SIZE or b"\0" in data[:8192]:
        return None
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.count("\n") + 1
    if len(text) > 20000 and len(text) / lines > 1000:  # minified bundle without .min in its name
        return None
    return text


def unquote(p):
    """C-style quoted path from git output."""
    if not (len(p) >= 2 and p[0] == p[-1] == '"'):
        return p
    s, out, i = p[1:-1], bytearray(), 0
    esc = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            if re.match(r"[0-7]{3}", s[i + 1:i + 4]):
                out.append(int(s[i + 1:i + 4], 8))
                i += 4
                continue
            out.append(esc.get(s[i + 1], ord(s[i + 1]) & 0xFF))
            i += 2
            continue
        out += s[i].encode("utf-8")
        i += 1
    return out.decode("utf-8", errors="replace")


def parse_diff(out):
    """({path: {line number: text}} of added lines, set of names on removed lines)."""
    added, removed = {}, set()
    cur, no, left_del, left_add = None, 0, 0, 0
    for b in out.split("\n"):
        if left_del or left_add:
            if b.startswith("+"):
                if cur is not None:
                    added[cur][no] = b[1:].rstrip("\r")
                no += 1
                left_add -= 1
            elif b.startswith("-"):
                removed.update(ID_RE.findall(b[1:]))
                removed.update(HYPHEN_RE.findall(b[1:]))
                left_del -= 1
            continue
        if b.startswith("+++ "):
            p = unquote(b[4:].rstrip("\t"))
            cur = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
            if cur is not None:
                added.setdefault(cur, {})
        elif b.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", b)
            if m:
                left_del = int(m.group(1)) if m.group(1) is not None else 1
                no = int(m.group(2))
                left_add = int(m.group(3)) if m.group(3) is not None else 1
    return added, removed


def cat_blobs(root, entries):
    """{path: bytes} for [(path, blob sha)] through one `git cat-file --batch`."""
    if not entries:
        return {}
    r = git(root, "cat-file", "--batch", data="".join(sha + "\n" for _, sha in entries).encode())
    out, pos, res = r.stdout, 0, {}
    for path, _ in entries:
        nl = out.find(b"\n", pos)
        if nl < 0:
            break
        head = out[pos:nl].split()
        pos = nl + 1
        if len(head) < 3 or head[1] == b"missing":
            continue
        size = int(head[2])
        res[path] = out[pos:pos + size]
        pos += size + 1
    return res


def load_change(root, mode, rev, paths):
    """(added, removed, tree texts, all paths, disk) for the chosen mode."""
    spec = ["--", *paths] if paths else []
    diff_opts = ["-U0", "--no-color", "--no-ext-diff", "--no-textconv", "-M"]
    disk = False
    if mode == "commit":
        sha = git(root, "rev-parse", "--verify", "-q", rev + "^{commit}").stdout.decode().strip()
        parent = git(root, "rev-parse", "--verify", "-q", sha + "^", check=False).stdout.decode().strip() or EMPTY_TREE
        out = git(root, "diff", *diff_opts, parent, sha, *spec).stdout
        tree_rev = sha
    elif mode == "range":
        if "..." in rev:
            left, right = rev.split("...", 1)
        elif ".." in rev:
            left, right = rev.split("..", 1)
        else:
            raise GitError("--range needs A..B")
        right = right or "HEAD"
        tree_rev = git(root, "rev-parse", "--verify", "-q", right + "^{commit}").stdout.decode().strip()
        git(root, "rev-parse", "--verify", "-q", (left or "HEAD") + "^{commit}")
        out = git(root, "diff", *diff_opts, rev if left else "HEAD.." + right, *spec).stdout
    elif mode == "staged":
        has_head = git(root, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0
        out = git(root, "diff", "--cached", *diff_opts, *([] if has_head else [EMPTY_TREE]), *spec).stdout
        tree_rev = None
    else:
        has_head = git(root, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0
        out = git(root, "diff", *diff_opts, "HEAD" if has_head else "--cached", *spec).stdout
        tree_rev = None
        disk = True
    added, removed = parse_diff(out.decode("utf-8", errors="replace"))
    texts, all_paths = {}, set()
    if mode in ("commit", "range"):
        listing = git(root, "ls-tree", "-r", "-z", "-l", tree_rev).stdout.decode("utf-8", errors="replace")
        want = []
        for item in listing.split("\0"):
            if not item or "\t" not in item:
                continue
            meta, path = item.split("\t", 1)
            f = meta.split()
            if len(f) < 4 or f[1] != "blob":
                continue
            all_paths.add(path)
            if not skipped(path) and f[3].isdigit() and int(f[3]) <= MAX_SIZE:
                want.append((path, f[2]))
        for path, data in cat_blobs(root, want).items():
            t = decode(data)
            if t is not None:
                texts[path] = t
    elif mode == "staged":
        listing = git(root, "ls-files", "-z", "-s").stdout.decode("utf-8", errors="replace")
        want = []
        for item in listing.split("\0"):
            if not item or "\t" not in item:
                continue
            meta, path = item.split("\t", 1)
            all_paths.add(path)
            if not skipped(path):
                want.append((path, meta.split()[1]))
        for path, data in cat_blobs(root, want).items():
            t = decode(data)
            if t is not None:
                texts[path] = t
    else:
        tracked = [p for p in git(root, "ls-files", "-z", "--cached").stdout.decode("utf-8", errors="replace").split("\0") if p]
        new = [p for p in git(root, "ls-files", "-z", "--others", "--exclude-standard", *spec).stdout.decode(
            "utf-8", errors="replace").split("\0") if p]
        others = [p for p in git(root, "ls-files", "-z", "--others", "--exclude-standard").stdout.decode(
            "utf-8", errors="replace").split("\0") if p] if paths else new
        for path in dict.fromkeys(tracked + others):
            full = os.path.join(root, path)
            if not os.path.isfile(full):
                continue
            all_paths.add(path)
            if skipped(path):
                continue
            try:
                if os.path.getsize(full) > MAX_SIZE:
                    continue
                with open(full, "rb") as fh:
                    t = decode(fh.read())
            except OSError:
                continue
            if t is not None:
                texts[path] = t
        for path in new:
            if path in texts:
                added[path] = {i: line for i, line in enumerate(texts[path].split("\n"), 1)}
    return added, removed, texts, all_paths, disk


# ---------------------------------------------------------------- JavaScript / TypeScript token scanner
class Tok(object):
    __slots__ = ("kind", "val", "line", "extra")

    def __init__(self, kind, val, line, extra=None):
        self.kind, self.val, self.line, self.extra = kind, val, line, extra

    def __repr__(self):
        return f"{self.kind}:{self.val!r}@{self.line}"


PUNCTS = sorted(""">>>= ... === !== **= <<= >>= >>> &&= ||= ??= => == != <= >= && || ?? ?. ++ -- += -= *= /= %= &= |= ^= ** << >>
{ } ( ) [ ] ; , < > + - * / % & | ^ ! ~ ? : = . @ #""".split(), key=len, reverse=True)


class Unfinished(Exception):
    pass


class JsScanner(object):
    """Tokens of a JS/TS/JSX file without comments; strings, templates, and regex literals are single tokens whose
    contents never become names. JSX text is skipped; tag names, attribute names, and attribute strings are tokens."""

    def __init__(self, src, jsx):
        self.s, self.n, self.i, self.line, self.jsx = src, len(src), 0, 1, jsx
        self.toks = []

    def add(self, kind, val, line=None, extra=None):
        self.toks.append(Tok(kind, val, self.line if line is None else line, extra))

    def expr_start(self):
        if not self.toks:
            return True
        t = self.toks[-1]
        if t.kind in ("num", "str", "tpl", "regex", "jsxend"):
            return False
        if t.kind == "id":
            return t.val in EXPR_KEYWORDS
        if t.kind == "punct":
            return t.val not in (")", "]", "}")
        return True

    def skip_space(self):
        s, n = self.s, self.n
        while self.i < n and s[self.i] in " \t\r\n\f\v﻿":
            if s[self.i] == "\n":
                self.line += 1
            self.i += 1

    def run(self):
        self.code(False)
        return self.toks

    def code(self, stop_brace):
        s, n = self.s, self.n
        depth = 0
        while self.i < n:
            c = s[self.i]
            if c == "\n":
                self.line += 1
                self.i += 1
            elif c in " \t\r\f\v﻿":
                self.i += 1
            elif c == "/" and s.startswith("//", self.i):
                j = s.find("\n", self.i)
                self.i = n if j < 0 else j
            elif c == "/" and s.startswith("/*", self.i):
                j = s.find("*/", self.i + 2)
                j = n if j < 0 else j
                body = s[self.i:j]
                if body.startswith("/**"):
                    self.add("jsdoc", body)
                self.line += body.count("\n")
                self.i = j + 2
            elif c.isalpha() or c in "_$" or (ord(c) > 127 and c.isidentifier()):
                j = self.i + 1
                while j < n and (s[j].isalnum() or s[j] in "_$" or (ord(s[j]) > 127 and s[j].isidentifier())):
                    j += 1
                self.add("id", s[self.i:j])
                self.i = j
            elif c.isdigit() or (c == "." and self.i + 1 < n and s[self.i + 1].isdigit()):
                j = self.i + 1
                while j < n and (s[j].isalnum() or s[j] in "._" or (s[j] in "+-" and s[j - 1] in "eE" and not s[self.i:j].lower().startswith("0x"))):
                    j += 1
                self.add("num", s[self.i:j])
                self.i = j
            elif c in "'\"":
                line = self.line
                self.add("str", self.string(c), line)
            elif c == "`":
                self.template()
            elif c == "/" and self.expr_start():
                self.regex()
            elif c == "<" and self.jsx and self.expr_start() and self.i + 1 < n and (s[self.i + 1].isalpha() or s[self.i + 1] == ">"):
                self.jsx_element()
            elif c == "{":
                depth += 1
                self.add("punct", "{")
                self.i += 1
            elif c == "}":
                if stop_brace and depth == 0:
                    self.i += 1
                    return
                depth -= 1
                self.add("punct", "}")
                self.i += 1
            else:
                for p in PUNCTS:
                    if s.startswith(p, self.i):
                        self.add("punct", p)
                        self.i += len(p)
                        break
                else:
                    self.i += 1
        if stop_brace:
            raise Unfinished()

    def string(self, q):
        s, n = self.s, self.n
        self.i += 1
        start = self.i
        while self.i < n:
            c = s[self.i]
            if c == "\\":
                if self.i + 1 < n and s[self.i + 1] == "\n":
                    self.line += 1
                self.i += 2
                continue
            if c == q:
                break
            if c == "\n":
                break
            self.i += 1
        val = s[start:self.i]
        if self.i < n and s[self.i] == q:
            self.i += 1
        return val

    def template(self):
        s, n = self.s, self.n
        self.i += 1
        start, line, left_open = self.i, self.line, False
        while self.i < n:
            c = s[self.i]
            if c == "\\":
                if self.i + 1 < n and s[self.i + 1] == "\n":
                    self.line += 1
                self.i += 2
                continue
            if c == "`":
                self.add("tpl", s[start:self.i], line, (left_open, False))
                self.i += 1
                return
            if c == "$" and s.startswith("${", self.i):
                self.add("tpl", s[start:self.i], line, (left_open, True))
                self.i += 2
                self.add("punct", ";", extra="t")
                self.code(True)
                self.add("punct", ";", extra="t")
                start, line, left_open = self.i, self.line, True
                continue
            if c == "\n":
                self.line += 1
            self.i += 1
        raise Unfinished()

    def regex(self):
        s, n = self.s, self.n
        line = self.line
        self.i += 1
        in_class = False
        while self.i < n:
            c = s[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "\n":
                break
            if c == "[":
                in_class = True
            elif c == "]":
                in_class = False
            elif c == "/" and not in_class:
                self.i += 1
                break
            self.i += 1
        while self.i < n and s[self.i].isalpha():
            self.i += 1
        self.add("regex", "", line)

    def jsx_element(self):
        s, n = self.s, self.n
        line = self.line
        self.i += 1
        self.skip_space()
        if self.i < n and s[self.i] == ">":
            self.i += 1
            self.jsx_children()
            return
        j = self.i
        while j < n and (s[j].isalnum() or s[j] in "_$.:-"):
            j += 1
        self.add("jsxtag", s[self.i:j], line)
        self.i = j
        while self.i < n:
            self.skip_space()
            if self.i >= n:
                break
            c = s[self.i]
            if s.startswith("/>", self.i):
                self.i += 2
                self.add("jsxend", "")
                return
            if c == ">":
                self.i += 1
                self.add("jsxopen", "")
                self.jsx_children()
                return
            if c == "{":
                self.i += 1
                self.add("punct", ";", extra="c")
                self.code(True)
                self.add("punct", ";", extra="c")
                continue
            if c.isalpha() or c in "_$":
                j = self.i
                while j < n and (s[j].isalnum() or s[j] in "_$:.-"):
                    j += 1
                name, aline = s[self.i:j], self.line
                self.add("jsxattr", name, aline)
                self.i = j
                self.skip_space()
                if self.i < n and s[self.i] == "=":
                    self.i += 1
                    self.skip_space()
                    if self.i < n and s[self.i] in "'\"":
                        q, start = s[self.i], self.i + 1
                        k = s.find(q, start)
                        k = n if k < 0 else k
                        val = s[start:k]
                        self.add("jsxstr", val, aline, name)
                        self.line += val.count("\n")
                        self.i = k + 1
                    elif self.i < n and s[self.i] == "{":
                        self.i += 1
                        self.add("punct", ";", extra="c")
                        self.code(True)
                        self.add("punct", ";", extra="c")
                continue
            if c == "<":  # a type argument or a stray character: not JSX after all
                raise Unfinished()
            self.i += 1
        raise Unfinished()

    def jsx_children(self):
        s, n = self.s, self.n
        while self.i < n:
            c = s[self.i]
            if c == "\n":
                self.line += 1
                self.i += 1
            elif c == "{":
                self.i += 1
                self.add("punct", ";", extra="c")
                self.code(True)
                self.add("punct", ";", extra="c")
            elif c == "<":
                if s.startswith("</", self.i):
                    k = s.find(">", self.i)
                    k = n if k < 0 else k
                    self.line += s.count("\n", self.i, k)
                    self.i = k + 1
                    self.add("jsxend", "")
                    return
                if self.i + 1 < n and (s[self.i + 1].isalpha() or s[self.i + 1] == ">"):
                    self.jsx_element()
                else:
                    self.i += 1
            else:
                self.i += 1
        raise Unfinished()


def js_tokens(text, ext):
    """(tokens, ok). JSX is tried first where it can appear; a scan that ends inside JSX is retried without it."""
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 6000))
    try:
        for jsx in ([True, False] if ext in JSX_EXT else [False]):
            sc = JsScanner(text, jsx)
            try:
                return sc.run(), True
            except Unfinished:
                if not jsx:
                    return sc.toks, False
            except RecursionError:
                return sc.toks, False
        return [], False
    finally:
        sys.setrecursionlimit(old)


def brackets(toks):
    pairs, stack = {}, []
    opener = {")": "(", "]": "[", "}": "{"}
    for i, t in enumerate(toks):
        if t.kind != "punct":
            continue
        if t.val in ("(", "[", "{"):
            stack.append(i)
        elif t.val in opener:
            while stack and toks[stack[-1]].val != opener[t.val]:
                stack.pop()
            if stack:
                j = stack.pop()
                pairs[i], pairs[j] = j, i
    return pairs


def is_p(t, *vals):
    return t is not None and t.kind == "punct" and t.val in vals


def is_id(t, *vals):
    return t is not None and t.kind == "id" and (not vals or t.val in vals)


def package_spec(spec):
    return not (spec.startswith((".", "/", "@/", "~/", "#", "src/")) or spec == "@")


class JsFile(object):
    """Bindings, definitions, and uses of one JS/TS file."""

    def __init__(self, path, text, ext, repo):
        self.path, self.ext, self.repo = path, ext, repo
        self.toks, self.ok = js_tokens(text, ext)
        self.t = self.toks
        self.pairs = brackets(self.toks)
        self.bind = defaultdict(set)
        self.destructured = []   # (key token index, origin)
        self.imports = []        # (name, token index of the name, first index, last index, spec)
        self.import_specs = []   # (spec, token index)
        self.defs = []           # (name, token index)
        self.analyse()

    def tok(self, i):
        return self.t[i] if 0 <= i < len(self.t) else None

    def params(self, a, b):
        """Names in a parameter list between token indexes a and b (exclusive)."""
        depth = 0
        for k in range(a, b):
            t = self.t[k]
            if t.kind == "punct" and t.val in ("{", "["):
                depth += 1
            elif t.kind == "punct" and t.val in ("}", "]"):
                depth -= 1
            elif t.kind == "id" and t.val not in RESERVED and not is_p(self.tok(k - 1), ".", "?."):
                if depth and is_p(self.tok(k + 1), ":"):
                    continue  # key of a destructured parameter
                self.bind[t.val].add("param")
                self.defs.append((t.val, k))

    def pattern(self, j):
        """(names, object keys, index after the pattern) for a binding pattern starting at j."""
        t = self.tok(j)
        if is_id(t):
            return [(t.val, j)], [], j + 1
        if not is_p(t, "{", "["):
            return [], [], j
        end = self.pairs.get(j)
        if end is None:
            return [], [], j + 1
        names, keys = [], []
        top_object = t.val == "{"
        depth = 0
        for k in range(j + 1, end):
            x = self.t[k]
            if x.kind == "punct" and x.val in ("{", "["):
                depth += 1
            elif x.kind == "punct" and x.val in ("}", "]"):
                depth -= 1
            elif x.kind == "id" and x.val not in RESERVED and not is_p(self.tok(k - 1), ".", "?.", "="):
                nxt = self.tok(k + 1)
                if is_p(nxt, ":"):
                    if top_object and depth == 0:
                        keys.append(k)
                    continue
                if is_p(nxt, ",", "}", "]", "=") or nxt is None or k + 1 == end:
                    names.append((x.val, k))
                    if top_object and depth == 0 and is_p(self.tok(k - 1), "{", ",", "..."):
                        if not is_p(self.tok(k - 1), "..."):
                            keys.append(k)
        return names, keys, end + 1

    def root_origin(self, name, called):
        if name in ("this", "super", "import"):
            return "lib"
        b = self.bind.get(name)
        if b:
            return "lib" if "lib" in b else "data" if ("data" in b or "param" in b) else None
        if name in JS_GLOBALS:
            return "lib"
        if called and self.repo.exists(name):
            return "data"
        return None

    def method_origin(self, methods, origin):
        for m in methods:
            if origin != "data":
                return origin
            if m in JS_DATA_METHODS or self.repo.defines(m):
                continue
            origin = "lib"
        return origin

    def expr_origin(self, k):
        """Origin of the value of the expression starting at token k: 'lib', 'data', or None (unknown)."""
        t = self.tok(k)
        while t is not None and (is_id(t, "await", "typeof", "void") or is_p(t, "(", "!", "...")):
            k += 1
            t = self.tok(k)
        if t is None:
            return None
        if is_id(t, "new"):
            n = self.tok(k + 1)
            if not is_id(n):
                return None
            o = self.root_origin(n.val, True)
            return "lib" if (o == "lib" or n.val in JS_GLOBALS) else "data"
        if is_id(t, "require") and is_p(self.tok(k + 1), "(") and self.tok(k + 2) is not None and self.tok(k + 2).kind == "str":
            return "lib" if package_spec(self.tok(k + 2).val) else "data"
        if t.kind in ("str", "num", "tpl", "regex") or is_p(t, "{", "["):
            return "data"
        if is_id(t, "function", "async", "class"):
            return "data"
        if t.kind != "id" or t.val in RESERVED - {"this", "super", "import"}:
            return None
        root, called, methods = t.val, False, []
        j = k + 1
        if is_p(self.tok(j), "("):
            called = True
            j = self.pairs.get(j, j) + 1
        while True:
            x = self.tok(j)
            if is_p(x, ".", "?.") and is_id(self.tok(j + 1)):
                if is_p(self.tok(j + 2), "("):
                    methods.append(self.tok(j + 1).val)
                    j = self.pairs.get(j + 2, j + 2) + 1
                else:
                    j += 2
            elif is_p(x, "["):
                j = self.pairs.get(j, j) + 1
            else:
                break
            if j <= k:
                break
        return self.method_origin(methods, self.root_origin(root, called))

    def chain_origin(self, j):
        """Origin of the object whose member is read: walks back from token j (the token before the dot)."""
        methods = []
        steps = 0
        while j >= 0 and steps < 200:
            steps += 1
            t = self.t[j]
            if is_p(t, ")"):
                o = self.pairs.get(j)
                if o is None or o == 0:
                    return None
                callee = self.t[o - 1]
                if callee.kind != "id" or callee.val in RESERVED - {"this", "super", "import"}:
                    return None
                if is_p(self.tok(o - 2), ".", "?."):
                    methods.insert(0, callee.val)
                    j = o - 3
                    continue
                return self.method_origin(methods, self.root_origin(callee.val, True))
            if is_p(t, "]"):
                o = self.pairs.get(j)
                if o is None or o == 0:
                    return None
                prev = self.t[o - 1]
                if prev.kind == "id" or is_p(prev, ")", "]"):
                    j = o - 1
                    continue
                return "data"  # array literal
            if t.kind == "id":
                if is_p(self.tok(j - 1), ".", "?."):
                    j -= 2
                    continue
                if t.val in RESERVED - {"this", "super", "import"}:
                    return None
                return self.method_origin(methods, self.root_origin(t.val, False))
            if t.kind in ("str", "tpl", "num", "regex"):
                return "lib"
            return None
        return None

    def analyse(self):
        t = self.t
        n = len(t)
        for i in range(n):
            x = t[i]
            if x.kind == "punct" and x.val == "=>":
                p = t[i - 1] if i else None
                if is_p(p, ")") and i - 1 in self.pairs:
                    self.params(self.pairs[i - 1] + 1, i - 1)
                elif is_id(p) and p.val not in RESERVED:
                    self.bind[p.val].add("param")
                    self.defs.append((p.val, i - 1))
                continue
            if x.kind != "id":
                continue
            v = x.val
            nxt = self.tok(i + 1)
            prev = self.tok(i - 1)
            if v == "import" and not is_p(nxt, "(", ".") and not is_p(prev, ".", "?."):
                self.import_statement(i)
            elif v == "export" and nxt is not None:
                pass
            elif v in ("const", "let", "var", "using") and not is_p(prev, ".", "?."):
                names, keys, j = self.pattern(i + 1)
                origin = None
                if is_p(self.tok(j), ":"):  # TypeScript annotation
                    depth, k = 0, j + 1
                    while k < n and k < j + 60:
                        y = t[k]
                        if y.kind == "punct" and y.val in ("(", "[", "{", "<"):
                            depth += 1
                        elif y.kind == "punct" and y.val in (")", "]", "}", ">"):
                            depth -= 1
                        elif depth <= 0 and y.kind == "punct" and y.val in ("=", ";", ","):
                            break
                        k += 1
                    j = k
                if is_p(self.tok(j), "=") or is_id(self.tok(j), "of", "in"):
                    origin = self.expr_origin(j + 1)
                    if is_id(self.tok(j + 1), "require") and self.tok(j + 3) is not None and self.tok(j + 3).kind == "str":
                        spec = self.tok(j + 3).val
                        self.import_specs.append((spec, j + 3))
                        last = self.pairs.get(j + 2, j + 3)
                        for name, k in names:
                            self.imports.append((name, k, i, last, spec))
                for name, k in names:
                    self.bind[name].add(origin or "unknown")
                    self.defs.append((name, k))
                for k in keys:
                    self.destructured.append((k, origin))
            elif v == "function":
                j = i + 1
                if is_p(self.tok(j), "*"):
                    j += 1
                if is_id(self.tok(j)):
                    self.bind[t[j].val].add("data")
                    self.defs.append((t[j].val, j))
                    j += 1
                if is_p(self.tok(j), "<"):  # TypeScript type parameters
                    while j < n and not is_p(t[j], "("):
                        j += 1
                if is_p(self.tok(j), "(") and j in self.pairs:
                    self.params(j + 1, self.pairs[j])
            elif v == "catch" and is_p(nxt, "(") and i + 1 in self.pairs:
                for k in range(i + 2, self.pairs[i + 1]):
                    if t[k].kind == "id":
                        self.bind[t[k].val].add("lib")
                        self.defs.append((t[k].val, k))
            elif v in ("class", "interface", "enum", "type", "namespace") and is_id(nxt) and not is_p(prev, ".", "?."):
                if v == "type" and not is_p(self.tok(i + 2), "=", "<"):
                    continue
                self.bind[nxt.val].add("data")
                self.defs.append((nxt.val, i + 1))
            elif v not in RESERVED and not is_p(prev, ".", "?."):
                if is_p(nxt, "=") and not is_p(prev, "{", ","):
                    self.bind[v].add(self.expr_origin(i + 2) or "unknown")
                elif is_p(nxt, "(") and i + 1 in self.pairs and is_p(self.tok(self.pairs[i + 1] + 1), "{"):
                    if prev is None or is_p(prev, "{", "}", ";", ",", "*") or is_id(prev, "async", "get", "set", "static", "public", "private", "protected", "override"):
                        self.defs.append((v, i))
                        self.params(i + 2, self.pairs[i + 1])
            # definitions that are not bindings: keys, assignments, member writes
            if v not in RESERVED:
                if is_p(nxt, ":") and is_p(prev, "{", ",", "(", ";", "}"):
                    self.defs.append((v, i))
                elif is_p(nxt, "?") and is_p(self.tok(i + 2), ":"):
                    self.defs.append((v, i))
                elif is_p(nxt, "=", "+=", "-=", "||=", "&&=", "??=") :
                    self.defs.append((v, i))
                elif x.kind == "id" and is_p(prev, "{", ",") and is_p(nxt, ",", "}") and self.in_object_literal(i):
                    self.defs.append((v, i))

    def in_object_literal(self, i):
        """Shorthand property `{ a, b }` on the right side of `=`, in a return, or as an argument."""
        depth = 0
        for k in range(i - 1, max(-1, i - 400), -1):
            y = self.t[k]
            if is_p(y, "}"):
                depth += 1
            elif is_p(y, "{"):
                if depth == 0:
                    p = self.tok(k - 1)
                    return is_p(p, "=", "(", ",", ":", "?", "[", "=>", "||", "&&", "??") or is_id(p, "return", "yield")
                depth -= 1
        return False

    def import_statement(self, i):
        t, n = self.t, len(self.t)
        j = i + 1
        names = []
        if j < n and t[j].kind == "str":  # import 'side-effect'
            self.import_specs.append((t[j].val, j))
            return
        while j < n and not is_id(t[j], "from") and not is_p(t[j], ";") and j < i + 400:
            x = t[j]
            if x.kind == "id" and x.val not in ("type", "typeof", "as") and not is_p(self.tok(j + 1), ","):
                pass
            if x.kind == "id" and x.val not in JS_KEYWORDS - {"type", "as"}:
                if x.val == "type" and is_id(self.tok(j + 1)) and not is_p(self.tok(j + 1), ","):
                    j += 1
                    continue
                if x.val == "as":
                    j += 1
                    continue
                if is_id(self.tok(j + 1), "as"):
                    j += 1
                    continue
                if x.val != "type":
                    names.append((x.val, j))
            j += 1
        if is_id(self.tok(j), "from") and self.tok(j + 1) is not None and self.tok(j + 1).kind == "str":
            spec = t[j + 1].val
            self.import_specs.append((spec, j + 1))
            origin = "lib" if package_spec(spec) else "data"
            for name, k in names:
                self.bind[name].add(origin)
                self.defs.append((name, k))
                self.imports.append((name, k, i, j + 1, spec))

    def string_defs(self):
        """Identifier-shaped string literals (codes, keys, ids) count as names defined by the file."""
        out = []
        for i, x in enumerate(self.t):
            if x.kind == "str" and IDENT_STR.fullmatch(x.val):
                out.append((x.val, i))
            elif x.kind == "jsxstr" and x.extra in ("id", "name"):
                for w in x.val.split():
                    out.append((w, i))
            elif x.kind == "jsxattr":
                out.append((x.val, i))
            elif x.kind == "tpl" and (";" in x.val or "=>" in x.val or "return" in x.val):
                # code in a template literal (a script evaluated in a page or a worker) declares names too
                for m in TPL_DECL.finditer(x.val):
                    out.append((m.group(1) or m.group(2), i))
        return out


# ---------------------------------------------------------------- Python
def py_tokens(text):
    """(tokens, ok): NAME -> id, OP -> punct, STRING -> str with its contents; comments dropped."""
    out, ok = [], True
    names_in_fstring = re.compile(r"(?<!\{)\{([^{}]*)\}")
    try:
        for tk in tokenize.generate_tokens(io.StringIO(text).readline):
            typ, s, (line, _), _, _ = tk
            if typ == tokenize.NAME:
                out.append(Tok("id", s, line))
            elif typ == tokenize.OP:
                out.append(Tok("punct", s, line))
            elif typ == tokenize.NUMBER:
                out.append(Tok("num", s, line))
            elif typ == tokenize.STRING:
                m = re.match(r"^([A-Za-z]*)('''|\"\"\"|'|\")(.*)\2$", s, re.S)
                prefix, body = (m.group(1).lower(), m.group(3)) if m else ("", s)
                extra = None
                if "f" in prefix:
                    extra = [nm for expr in names_in_fstring.findall(body) for nm in ID_RE.findall(expr)]
                out.append(Tok("str", body, line, extra))
            elif typ == tokenize.NEWLINE:
                out.append(Tok("nl", "", line))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        ok = False
    return out, ok


class PyFile(object):
    def __init__(self, path, text):
        self.path = path
        self.t, self.ok = py_tokens(text)
        self.defs, self.imports, self.rel_imports = [], [], []
        self.star = False
        self.analyse()

    def tok(self, i):
        return self.t[i] if 0 <= i < len(self.t) else None

    def analyse(self):
        t, n = self.t, len(self.t)
        stmt_start = True
        for i, x in enumerate(t):
            if x.kind == "nl":
                stmt_start = True
                continue
            starts = stmt_start
            stmt_start = False
            if x.kind != "id":
                continue
            v, nxt, prev = x.val, self.tok(i + 1), self.tok(i - 1)
            if starts and v in ("import", "from"):
                self.import_statement(i)
            if v in ("def", "class", "global", "nonlocal") and is_id(nxt):
                self.defs.append((nxt.val, i + 1))
                if v == "def" and is_p(self.tok(i + 2), "("):
                    depth, k = 0, i + 2
                    while k < n:
                        y = t[k]
                        if is_p(y, "(", "[", "{"):
                            depth += 1
                        elif is_p(y, ")", "]", "}"):
                            depth -= 1
                            if depth == 0:
                                break
                        elif y.kind == "id" and depth == 1 and (is_p(t[k - 1], "(", ",", "*", "**")):
                            self.defs.append((y.val, k))
                        k += 1
            elif v == "lambda":
                k = i + 1
                while k < n and not is_p(t[k], ":"):
                    if t[k].kind == "id":
                        self.defs.append((t[k].val, k))
                    k += 1
            elif v == "for":
                k = i + 1
                while k < n and not is_id(t[k], "in") and k < i + 30:
                    if t[k].kind == "id":
                        self.defs.append((t[k].val, k))
                    k += 1
            elif v == "as" and is_id(nxt):
                self.defs.append((nxt.val, i + 1))
            elif is_p(nxt, "=", ":=", "+=", "-=", "|=") and not is_p(prev, "."):
                self.defs.append((v, i))
            elif is_p(nxt, "=", ":=") and is_p(prev, "."):
                self.defs.append((v, i))
            elif is_p(nxt, ":") and is_p(prev, ",", "(") is False and starts:
                self.defs.append((v, i))  # annotated assignment at statement start
            elif is_p(nxt, ",") and starts:
                k = i
                while k < n and not is_p(t[k], "=") and t[k].kind != "nl":
                    k += 1
                if k < n and is_p(t[k], "="):
                    for q in range(i, k):
                        if t[q].kind == "id":
                            self.defs.append((t[q].val, q))

    def import_statement(self, i):
        t, n = self.t, len(self.t)
        end = i
        while end < n and t[end].kind != "nl":
            end += 1
        if t[i].val == "from":
            k, dots = i + 1, 0
            while k < end and is_p(t[k], ".", "..."):
                dots += len(t[k].val)
                k += 1
            mod = []
            while k < end and not is_id(t[k], "import"):
                if t[k].kind == "id":
                    mod.append(t[k].val)
                k += 1
            if mod and mod[0] == "__future__":
                return
            if dots:
                self.rel_imports.append((dots, mod, i))
            k += 1
            while k < end:
                y = t[k]
                if is_p(y, "*"):
                    self.star = True
                elif y.kind == "id" and y.val != "as":
                    if is_id(self.tok(k + 1), "as"):
                        k += 1
                        continue
                    self.defs.append((y.val, k))
                    self.imports.append((y.val, k, i, end))
                k += 1
        else:
            k = i + 1
            while k < end:  # `import a.b`, `import a.b as c`, separated by commas
                seg = k
                while k < end and not is_p(t[k], ","):
                    k += 1
                ids = [q for q in range(seg, k) if t[q].kind == "id"]
                if ids:
                    q = ids[-1] if any(t[x].val == "as" for x in ids) else ids[0]
                    self.defs.append((t[q].val, q))
                    self.imports.append((t[q].val, q, i, end))
                k += 1

    def string_defs(self):
        return [(x.val, i) for i, x in enumerate(self.t) if x.kind == "str" and IDENT_STR.fullmatch(x.val)]


# ---------------------------------------------------------------- repo corpus
class Repo(object):
    def __init__(self, texts, added, removed, all_paths, root, disk):
        self.texts, self.added, self.removed, self.all_paths, self.root, self.disk = texts, added, removed, all_paths, root, disk
        self.ids, self.words = set(), set()
        self.new_defs = set()
        self.dirs = set()
        for p in all_paths:
            parts = p.split("/")
            for k in range(1, len(parts)):
                self.dirs.add("/".join(parts[:k]))
        self.stems = set()
        for p in all_paths:
            base = p.rsplit("/", 1)[-1]
            self.stems.update(ID_RE.findall(base))
        for path, text in texts.items():
            if ext_of(path) in DOC_EXT:
                continue
            new = added.get(path)
            if new:
                lines = text.split("\n")
                text = "\n".join(line for k, line in enumerate(lines, 1) if k not in new)
            self.ids.update(ID_RE.findall(text))
            self.words.update(HYPHEN_RE.findall(text))
        self._defsrc = None
        self._defs_cache = {}

    def exists(self, name):
        return name in self.ids or name in self.new_defs or name in self.removed

    def exists_word(self, w):
        return w in self.words or w in self.ids or w in self.new_defs or w in self.removed

    def defines(self, name):
        """True when a non-test code file defines `name` as a function, method, key, or assignment target."""
        if name in self._defs_cache:
            return self._defs_cache[name]
        if self._defsrc is None:
            self._defsrc = "\n".join(t for p, t in self.texts.items()
                                     if ext_of(p) in JS_EXT | PY_EXT and not TEST_PATH.search(p))
        e = re.escape(name)
        rx = re.compile(r"\bfunction\s*\*?\s*" + e + r"\b|\bdef\s+" + e + r"\b|\bclass\s+" + e + r"\b|(?<![\w$.?&])" + e +
                        r"\s*[:=]\s*(?:async\s+)?(?:function\b|lambda\b|\([^()\n]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)|"
                        r"^\s*(?:async\s+|static\s+|public\s+|private\s+|protected\s+|get\s+|set\s+)*" +
                        e + r"\s*\([^)\n]*\)\s*(?::[^{\n]*)?\{", re.M)
        res = bool(rx.search(self._defsrc))
        self._defs_cache[name] = res
        return res

    def path_exists(self, rel):
        if rel in self.all_paths or rel in self.dirs:
            return True
        return self.disk and os.path.exists(os.path.join(self.root, rel))


def norm_path(base_dir, spec):
    parts = []
    for b in ((base_dir + "/" if base_dir else "") + spec).split("/"):
        if b == "..":
            if parts:
                parts.pop()
            else:
                return None
        elif b not in (".", ""):
            parts.append(b)
    return "/".join(parts)


def resolve_import(repo, path, spec):
    spec = spec.split("?", 1)[0].split("#", 1)[0]
    base = path.rsplit("/", 1)[0] if "/" in path else ""
    q = norm_path(base, spec)
    if q is None:
        return True  # outside the repo: not ours to judge
    cands = [q] + [q + e for e in RESOLVE_EXT] + [q + "/index" + e for e in RESOLVE_EXT]
    for js, ts in ((".js", ".ts"), (".js", ".tsx"), (".jsx", ".tsx"), (".mjs", ".mts"), (".cjs", ".cts")):
        if q.endswith(js):
            cands.append(q[:-len(js)] + ts)
            cands.append(q[:-len(js)] + ".d.ts")
    return any(repo.path_exists(c) for c in cands)


# ---------------------------------------------------------------- checks
class Marks(object):
    def __init__(self, added):
        self.added = added
        self.items, self.seen = [], set()

    def add(self, cls, name, path, line):
        key = (cls, name, path)
        if key in self.seen:
            return
        self.seen.add(key)
        text = self.added.get(path, {}).get(line, "")
        self.items.append({"class": cls, "name": name, "file": path, "line": line, "text": text.strip()})


def check_js(f, repo, marks, new, style):
    t = f.t
    pairs = f.pairs

    def on_new(k):
        return t[k].line in new

    # property reads on repo data
    for i, x in enumerate(t):
        if not (x.kind == "punct" and x.val in (".", "?.")):
            continue
        y = f.tok(i + 1)
        if not is_id(y) or y.line not in new or i == 0:
            continue
        nxt = f.tok(i + 2)
        if is_p(nxt, "(", "=", "+=", "-=", "||=", "&&=", "??=", "++", "--") or (nxt is not None and nxt.kind == "tpl") \
                or (is_p(nxt, "?.") and is_p(f.tok(i + 3), "(")):
            continue
        name = y.val
        if name in JS_MEMBERS or repo.exists(name):
            continue
        if f.chain_origin(i - 1) != "data":
            continue
        marks.add("UNDEFINED", name, f.path, y.line)
    for k, origin in f.destructured:
        if origin == "data" and on_new(k):
            name = t[k].val
            if name not in JS_MEMBERS and not repo.exists(name):
                marks.add("UNDEFINED", name, f.path, t[k].line)
    # plain calls
    for i, x in enumerate(t):
        if x.kind != "id" or x.line not in new or not is_p(f.tok(i + 1), "("):
            continue
        v, prev = x.val, f.tok(i - 1)
        if v in RESERVED or v in JS_GLOBALS or v == "async" or is_p(prev, ".", "?.") or is_id(prev, "function", "class", "def"):
            continue
        close = pairs.get(i + 1)
        if close is not None and is_p(f.tok(close + 1), "{") and (prev is None or is_p(prev, "{", "}", ";", ",") or is_id(prev, "async", "get", "set", "static")):
            continue  # method definition
        if v in f.bind or repo.exists(v):
            continue
        marks.add("UNDEFINED", v, f.path, x.line)
    # JSX attribute values, id references, classes, var(--x) in strings
    tag = ""
    for i, x in enumerate(t):
        if x.kind == "jsxtag":
            tag = x.val
            continue
        if x.kind in ("str", "tpl", "jsxstr") and x.line in new:
            txt = x.val
            for m in CSSVAR_USE.finditer(txt):
                if m.group(2) == ")" and m.group(1) not in style.vars:
                    marks.add("UNDEFINED", m.group(1), f.path, x.line + txt.count("\n", 0, m.start()))
        if x.kind == "jsxstr" and x.line in new:
            attr, val = x.extra, x.val.strip()
            if attr in ID_REF_ATTRS:
                for w in val.split():
                    if not repo.exists_word(w) and w not in style.new_ids:
                        marks.add("UNDEFINED", w, f.path, x.line)
            elif tag[:1].isupper() and attr not in NO_VALUE_ATTRS and not attr.startswith(("on", "aria-", "data-")) \
                    and WORD_RE.fullmatch(val) and not repo.exists_word(val):
                marks.add("UNDEFINED", val, f.path, x.line)
    # relative imports
    for spec, k in f.import_specs:
        if on_new(k) and spec.startswith(("./", "../")) and not resolve_import(repo, f.path, spec):
            marks.add("UNDEFINED", spec, f.path, t[k].line)
    # dynamic calls
    for i in range(len(t) - 3):
        if is_p(t[i], "[") and t[i + 1].kind == "str" and is_p(t[i + 2], "]") and is_p(t[i + 3], "(") and t[i].line in new:
            if IDENT_STR.fullmatch(t[i + 1].val) and i > 0 and (t[i - 1].kind == "id" or is_p(t[i - 1], ")", "]")):
                marks.add("DYNAMIC-CALL", t[i + 1].val, f.path, t[i].line)
    # unused imports
    if f.imports:
        uses = defaultdict(int)
        ranges = []
        for _, _, a, b, _ in f.imports:
            ranges.append((a, b))
        inside = set()
        for a, b in ranges:
            inside.update(range(a, b + 1))
        has_jsx = False
        for i, x in enumerate(t):
            if x.kind == "id" and i not in inside and not is_p(f.tok(i - 1), ".", "?."):
                uses[x.val] += 1
            elif x.kind == "jsxtag":
                has_jsx = True
                uses[x.val.split(".")[0]] += 1
            elif x.kind == "jsdoc":
                for w in ID_RE.findall(x.val):
                    uses[w] += 1
        for name, k, a, b, spec in f.imports:
            if not on_new(a) or uses.get(name):
                continue
            if name == "React" and has_jsx:
                continue
            marks.add("UNUSED-IMPORT", name, f.path, t[k].line)


def check_py(f, repo, marks, new):
    t = f.t
    if not f.path.endswith("__init__.py"):
        stmt_ranges = set()
        for _, _, a, b in f.imports:
            stmt_ranges.update(range(a, b + 1))
        uses = defaultdict(int)
        for i, x in enumerate(t):
            if x.kind == "id" and i not in stmt_ranges and not is_p(f.tok(i - 1), "."):
                uses[x.val] += 1
            elif x.kind == "str":
                if x.extra:
                    for w in x.extra:
                        uses[w] += 1
                if IDENT_STR.fullmatch(x.val):
                    uses[x.val] += 1
                else:
                    for w in ID_RE.findall(x.val) if re.fullmatch(r"[\w\[\]., |]+", x.val) else ():
                        uses[w] += 1  # string annotations such as "Optional[Foo]"
        for name, k, a, b in f.imports:
            if t[a].line in new and not uses.get(name) and name != "_":
                marks.add("UNUSED-IMPORT", name, f.path, t[k].line)
    for i, x in enumerate(t):
        if x.kind != "id" or x.line not in new:
            continue
        nxt, prev = f.tok(i + 1), f.tok(i - 1)
        if is_p(nxt, "(") and not f.star:
            v = x.val
            if v in PY_BUILTINS or is_p(prev, ".") or is_id(prev, "def", "class"):
                continue
            if not repo.exists(v):
                marks.add("UNDEFINED", v, f.path, x.line)
    for i in range(len(t) - 3):
        if is_p(t[i], "[") and t[i + 1].kind == "str" and is_p(t[i + 2], "]") and is_p(t[i + 3], "(") and t[i].line in new:
            if IDENT_STR.fullmatch(t[i + 1].val) and i > 0 and (t[i - 1].kind == "id" or is_p(t[i - 1], ")", "]")):
                marks.add("DYNAMIC-CALL", t[i + 1].val, f.path, t[i].line)
    base = f.path.rsplit("/", 1)[0] if "/" in f.path else ""
    for dots, mod, k in f.rel_imports:
        if t[k].line not in new or not mod:
            continue
        d = base
        for _ in range(dots - 1):
            d = d.rsplit("/", 1)[0] if "/" in d else ""
        q = "/".join(([d] if d else []) + mod)
        if not (repo.path_exists(q + ".py") or repo.path_exists(q + ".pyi") or repo.path_exists(q) or repo.path_exists(q + "/__init__.py")):
            marks.add("UNDEFINED", "." * dots + ".".join(mod), f.path, t[k].line)


class Style(object):
    """Custom properties with a definition, and ids defined on new lines."""

    def __init__(self, repo):
        self.vars, self.new_ids = set(), set()
        for path, text in repo.texts.items():
            if ext_of(path) in DOC_EXT:
                continue
            for m in CSSVAR_DEF.finditer(text):
                self.vars.add(m.group(1) or m.group(2) or m.group(3))
        for path, new in repo.added.items():
            if ext_of(path) in JS_EXT | HTML_EXT:
                for line in new.values():
                    self.new_ids.update(HTML_ID_ATTR.findall(line))


def check_css(path, repo, marks, new, style):
    in_comment = False
    for no in sorted(new):
        line = new[no]
        s = line
        if in_comment:
            j = s.find("*/")
            if j < 0:
                continue
            s, in_comment = s[j + 2:], False
        s = re.sub(r"/\*.*?\*/", " ", s)
        if "/*" in s:
            s, in_comment = s[:s.find("/*")], True
        for m in CSSVAR_USE.finditer(s):
            if m.group(2) == ")" and m.group(1) not in style.vars:
                marks.add("UNDEFINED", m.group(1), path, no)


def check_html(path, repo, marks, new, style):
    check_css(path, repo, marks, new, style)


def doc_names(text, only=None):
    """[(name, line, block)] in code spans and fenced code blocks (block = first line of the block, 0 for spans);
    `only` limits to these line numbers. Quoted values are data, not names; quoted keys ("name": 1) stay."""
    out, fence, block = [], None, 0
    for no, line in enumerate(text.split("\n"), 1):
        m = FENCE.match(line)
        if fence is None and m:
            fence, block = m.group(1)[0] * 3, no
            continue
        if fence is not None:
            if line.strip().startswith(fence):
                fence = None
                continue
            if only is None or no in only:
                out += [(x, no, block) for x in DOC_NAME.findall(QUOTED_VALUE.sub(" ", line))]
            continue
        if only is not None and no not in only:
            continue
        for sp in CODE_SPAN.finditer(line):
            out += [(x, no, 0) for x in DOC_NAME.findall(QUOTED_VALUE.sub(" ", sp.group(2)))]
    return out


def check_doc(path, text, repo, marks, new, info_docs):
    def known(w):
        return repo.exists(w) or w in repo.stems or w in JS_GLOBALS or w in JS_MEMBERS or w in PY_BUILTINS

    news = doc_names(text, set(new))
    if not news:
        return
    every = doc_names(text)
    names = {w for w, _, _ in every}
    missing_all = {w for w in names if not known(w)}
    missing_new = [(w, no, b) for w, no, b in news if not known(w)]
    if not missing_new:
        return
    if len(names) >= 5 and len(missing_all) * 2 > len(names):
        info_docs.append((path, len(missing_all), len(names), 0))
        return
    # a code block whose names are mostly absent is a proposal or code of another system
    per_block = {}
    for w, _, b in every:
        if b:
            per_block.setdefault(b, set()).add(w)
    loose = {b for b, ws in per_block.items() if len(ws) >= 4 and sum(1 for w in ws if not known(w)) * 2 > len(ws)}
    skipped_blocks = {b for _, _, b in missing_new if b in loose}
    for w, no, b in missing_new:
        if b not in loose:
            marks.add("DOC", w, path, no)
    if skipped_blocks:
        info_docs.append((path, 0, 0, len(skipped_blocks)))


def run(root, mode, rev, paths):
    added, removed, texts, all_paths, disk = load_change(root, mode, rev, paths)
    repo = Repo(texts, added, removed, all_paths, root, disk)
    marks = Marks(added)
    info, not_checked = [], defaultdict(int)
    parsed = {}
    for path, new in added.items():
        if not new or skipped(path) or path not in texts:
            continue
        e = ext_of(path)
        if e in JS_EXT:
            parsed[path] = JsFile(path, texts[path], e, repo)
        elif e in PY_EXT:
            parsed[path] = PyFile(path, texts[path])
        elif e in PARSED_EXT:
            pass
        else:
            if e not in QUIET_EXT:
                not_checked[e or "(no extension)"] += 1
            if e not in DOC_EXT:
                for line in new.values():  # unparsed code: names on new lines count as defined
                    repo.new_defs.update(ID_RE.findall(line))
                    repo.words.update(HYPHEN_RE.findall(line))
    for path, f in parsed.items():
        new = added[path]
        for name, k in f.defs + f.string_defs():
            if f.t[k].line in new:
                repo.new_defs.add(name)
        if not f.ok:
            not_checked[ext_of(path) + " (scan stopped early)"] += 1
    for path, new in added.items():
        if ext_of(path) in CSS_EXT | HTML_EXT and path in texts and not skipped(path):
            for line in new.values():
                repo.new_defs.update(HYPHEN_RE.findall(line))
                repo.new_defs.update(HTML_ID_ATTR.findall(line))
    style = Style(repo)
    info_docs = []
    checked = 0
    for path in sorted(added):
        new = added[path]
        if not new or skipped(path) or path not in texts:
            continue
        checked += 1
        e = ext_of(path)
        if path in parsed:
            f = parsed[path]
            (check_js(f, repo, marks, new, style) if e in JS_EXT else check_py(f, repo, marks, new))
        elif e in CSS_EXT:
            check_css(path, repo, marks, new, style)
        elif e in HTML_EXT:
            check_html(path, repo, marks, new, style)
        elif e in MD_EXT:
            check_doc(path, texts[path], repo, marks, new, info_docs)
    if info_docs:
        whole = [f"{p} ({m} of {n} names)" for p, m, n, b in info_docs if not b]
        blocks = [f"{p} ({b} code block{'s' if b > 1 else ''})" for p, m, n, b in info_docs if b]
        info.append("DOC not marked: most code names in " + ", ".join(whole + blocks) + " are absent from the code "
                    "(written before the code, a proposal, or about another system)")
    marks.items.sort(key=lambda m: (m["file"], m["line"], m["class"], m["name"]))
    return marks.items, info, dict(not_checked), checked


def main():
    ap = argparse.ArgumentParser(description="Facts about the lines a change adds: UNDEFINED, UNUSED-IMPORT, "
                                             "DYNAMIC-CALL, DOC. Read-only; exit 0 when the check ran.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--worktree", action="store_true", help="tracked changes vs HEAD + new untracked files (default)")
    mode.add_argument("--staged", action="store_true", help="staged changes; the tree is the index")
    mode.add_argument("--commit", metavar="C", help="commit C against its parent; the tree is C")
    mode.add_argument("--range", metavar="A..B", help="changes A..B; the tree is B")
    ap.add_argument("--docs", action="store_true", help="also list DOC marks and doc INFO lines (without it: one count "
                                                         "line, and DOC is left out of the final count)")
    ap.add_argument("--json", action="store_true", help="machine-readable output (version 1)")
    ap.add_argument("paths", nargs="*", help="limit the checked changed files to these paths")
    a = ap.parse_args()
    setup_output()
    try:
        r = git(os.getcwd(), "rev-parse", "--show-toplevel", check=False)
    except GitError as e:
        print(f"ERROR: {e}")
        return 2
    if r.returncode != 0:
        print("ERROR: not inside a git repository.")
        return 2
    root = r.stdout.decode("utf-8", errors="replace").strip()
    # Relative paths are joined to git's own prefix for the current folder, not compared with the
    # toplevel string: on Windows the temp folder can be an 8.3 short name (RUNNER~1) while git
    # reports the long name, and relpath between the two leaves the repository.
    prefix = git(os.getcwd(), "rev-parse", "--show-prefix", check=False).stdout.decode(
        "utf-8", errors="replace").strip()
    paths = []
    for p in a.paths:
        if os.path.isabs(p):
            rel = os.path.relpath(os.path.realpath(p), os.path.realpath(root)).replace("\\", "/")
        else:
            rel = posixpath.normpath(posixpath.join(prefix, p.replace("\\", "/")))
        paths.append(rel)
    mode_name = "commit" if a.commit else "range" if a.range else "staged" if a.staged else "worktree"
    try:
        marks, info, not_checked, checked = run(root, mode_name, a.commit or a.range, paths)
    except GitError as e:
        print(f"ERROR: {e}")
        return 2
    docs_hidden = 0
    if not a.docs:  # DOC marks and the doc INFO lines (every INFO line is about docs) are head material
        docs_hidden = sum(1 for m in marks if m["class"] == "DOC")
        marks = [m for m in marks if m["class"] != "DOC"]
        info = []
    if a.json:
        print(json.dumps({"version": 1, "mode": mode_name, "files": checked, "marks": marks, "info": info,
                          "not_checked": not_checked, "docs_hidden": docs_hidden}, ensure_ascii=False))
        return 0
    classes = ("UNDEFINED", "UNUSED-IMPORT", "DYNAMIC-CALL") + (("DOC",) if a.docs else ())
    per_class = defaultdict(list)
    for m in marks:
        per_class[m["class"]].append(m)
    for cls in classes:
        items = per_class.get(cls, [])
        for m in items[:MAX_PER_CLASS]:
            text = m["text"] if len(m["text"]) <= 160 else m["text"][:157] + "..."
            print(f"{cls} {m['name']} {m['file']}:{m['line']} | {text}")
        if len(items) > MAX_PER_CLASS:
            print(f"{cls} ... {len(items) - MAX_PER_CLASS} more (--json lists all)")
    for x in info:
        print(f"INFO {x}")
    if not_checked:
        print("not checked: " + ", ".join(f"{e} {n} file{'s' if n != 1 else ''}" for e, n in sorted(not_checked.items())))
    for cls in classes:
        if per_class.get(cls):
            print(f"{cls}: {LEGEND[cls]}")
    if docs_hidden:
        print(f"DOC: {docs_hidden} name{'s' if docs_hidden != 1 else ''} in changed docs not found in code "
              "(run with --docs to list them)")
    if not checked:
        hint = "; if the change is already committed, use --commit <C> or --range A..B" if mode_name in (
            "worktree", "staged") else ""
        print(f"No changed files to check in --{mode_name} mode{hint}.")
    print(f"CHECK-DIFF: {len(marks)} marks in {len({m['file'] for m in marks})} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
