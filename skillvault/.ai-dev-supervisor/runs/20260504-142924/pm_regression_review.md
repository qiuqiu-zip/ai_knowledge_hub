# PM Regression Review

Status: NEEDS_DEVELOPER_INVESTIGATION

## PM Visual Feedback

The current login page is still not acceptable. The page still looks almost the same as before:
- The card is still visually too large.
- There is too much blank space inside the card.
- The form still uses an awkward horizontal label/input layout.
- The language selector at the bottom-right feels detached.
- The design does not yet look like a modern enterprise SaaS login page.

## Required Direction

Do not make tiny numeric tweaks again. Rework the visual hierarchy while preserving all logic:
- Keep the script section unchanged.
- Preserve username and password v-model bindings.
- Preserve login button click, loading and disabled behavior.
- Preserve language selector and changeLocale.
- Preserve privacy notice bar.
- Do not add new features or dependencies.

Developer must investigate how to safely redesign the template and scoped CSS before a second implementation.
