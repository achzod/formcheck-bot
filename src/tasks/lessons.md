# Lessons

## 2026-03-15

- When the user says "MiniMax does the analysis, local code only formats it", treat that as a hard architectural contract.
- Do not rely on environment flags alone for source-first behavior. Enforce the contract in code and protect it with tests.
- Do not add local semantic overrides on top of a third-party analysis engine unless the user explicitly asks for that layer.
- For non-trivial tasks, write the execution plan to `tasks/todo.md` before implementation and finish with a review section.
- After a user correction about process or quality expectations, capture the pattern immediately in `tasks/lessons.md`.
