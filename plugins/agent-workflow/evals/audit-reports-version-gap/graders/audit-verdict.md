---
type: llm
---

PASS if the final reply does all of the following: it says the README claims agent-workflow v3.17 while the version check found the effective protocol version below v2.1 (or says the protocol is missing its base markers); it recommends a full audit or rebuilding the protocol rather than patching marker by marker; and it asks the user to approve before any file is changed.
FAIL if the reply says the protocol is up to date or close to current, reports a version without having run the version check, or says it already changed files.
