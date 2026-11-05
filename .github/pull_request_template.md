## Task

Task ID from the task list (for example B-11) and what this pull request does in one sentence.

## Screenshots

Phone or browser screenshots of the screen, including the empty and error states.
Owner dashboard: dark and light theme.

## Checklist

- [ ] Uses the generated API types (`npm run gen:api`), no hand-written response types
- [ ] Loading, empty, error and success states
- [ ] Error codes from the handoff are handled; field errors show under the right input
- [ ] Prices, totals and statuses come from the server, never calculated
- [ ] Buttons that call the API are disabled while the request runs
- [ ] `npm run lint` and `npm run typecheck` pass
- [ ] No `.env`, passwords, tokens or secrets in the diff
- [ ] No changes under `backend/`
