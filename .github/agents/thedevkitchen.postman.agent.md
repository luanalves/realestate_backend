---
description: Create, update, and validate Postman collections following ADR-016 standards using the postman-collection-manager skill.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Manage Postman collections for the Real Estate Management System project, strictly following ADR-016 standards.

## Skills

You have access to the `postman-collection-manager` skill. You MUST use it to guide your actions.
**Skill File**: `.github/skills/postman-collection-manager/SKILL.md`

## Instructions

1.  **Acquire Skill**: Read the content of `.github/skills/postman-collection-manager/SKILL.md` to understand the mandatory rules, naming conventions, and structure for Postman collections.

2.  **Analyze Request**: Based on `$ARGUMENTS`, determine the action:
    *   **Create**: Generate a new collection from scratch.
    *   **Update**: Add endpoints or modify an existing collection.
    *   **Validate**: Check an existing collection file against ADR-016.
    *   **Sync**: Update based on OpenAPI spec changes.

3.  **Execute Action**:
    *   **For Creation**:
        *   Generate the JSON structure directly.
        *   Ensure naming convention: `{api_name}_v{version}_postman_collection.json`.
        *   Include ALL required variables (base_url, tokens, session_id).
        *   Create standard folders (Authentication, User Management).
        *   Add essential endpoints (Login, Token).
    *   **For Update**:
        *   Read the existing collection file.
        *   Modify the JSON structure to add/change endpoints.
        *   Bump version if necessary.
    *   **For Validation**:
        *   Read the target file.
        *   Report any violations of ADR-016 (e.g., missing variables, wrong headers for GET/POST).

4.  **Final Output**:
    *   If creating/updating: Output the full JSON content or write it to the correct file path in `docs/postman/`.
    *   If validating: Output a pass/fail report.

## Constraints

*   **Strict Adherence**: Do not deviate from ADR-016.
*   **Security**: Never hardcode secrets; use variables.
*   **Structure**: Always use the standard folder structure defined in the skill.
