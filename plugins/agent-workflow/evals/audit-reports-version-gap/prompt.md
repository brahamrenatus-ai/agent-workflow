---
description: AUDIT on a project whose README claims v3.17 while its protocol files are nearly empty. The skill should run check_version.py, report the gap between written and effective version, recommend a full audit, and change nothing before the user approves. Needs Bash, so it runs only where Claude Code has a sandbox backend (macOS, Linux, WSL); on native Windows the run is refused.
tags: [audit, shell]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write]
expected_outcome: Reply reports written v3.17 vs effective below v2.1 from check_version.py, recommends a full audit, asks before changing files.
---

Repo ini memakai alur head/executor untuk agen AI. Tolong audit protokolnya: sudah versi berapa, dan apa saja yang perlu diperbarui?
