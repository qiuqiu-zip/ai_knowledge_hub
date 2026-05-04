# Developer Re-Investigation

## PM Issues
- ISSUE-UI-001: The implementation is too conservative. It only shrinks dimensions and moves the language selector, but does not achieve a polished SaaS login page.
- ISSUE-UI-002: The current design still looks bulky and unfinished.

## Read-only Analysis
# Developer Investigation

## Current Implementation Summary
Read target files and related local imports.

## Entry Points & Dependencies
- frontend/src/api/client.ts
- frontend/src/stores/auth.ts
- frontend/src/i18n/index.ts

## Risks
- Avoid changing business logic contracts in script/auth/router/i18n.
