# Frontend Instructions (Vite + React SPA)

## Do
- Build only admin console features in `frontend/`.
- Use React + TypeScript + Tailwind + shadcn/ui.
- Keep API clients aligned to `/api/v1/admin/*` and `/api/v1/data/*`.
- Implement wizard UX for Module 2 with a rich SQL editor.
- Use Monaco (`@monaco-editor/react`) or CodeMirror 6 (`@uiw/react-codemirror`) for SQL authoring.
- Provide explicit validation errors for bind params and auth setup.
- Write component tests for wizard steps and critical forms.

## Do Not
- Do not implement backend business logic in frontend.
- Do not hardcode secrets, tokens, or private endpoints.
- Do not call unversioned API paths.
- Do not bypass typed client models.

## Frontend Validation Commands
- `cd frontend && npm install`
- `cd frontend && npm run dev`
- `cd frontend && npm run eslint`
- `cd frontend && npm run prettier:check`
- `cd frontend && npm run test`

## UI Contract Rules
- Wizard must enforce bind variable awareness (`:param_name`).
- Endpoint creation UI must expose auth assignment and data strategy selection.
- Show clear status for live-query vs scheduled-snapshot behavior.
- Surface backend validation errors verbatim when safe.

## Stop Conditions
- API payload uncertainty: check backend OpenAPI/spec and existing API client types.
- Ambiguous workflow state: inspect existing wizard store/components before adding new state model.
