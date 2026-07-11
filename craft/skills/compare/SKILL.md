---
name: compare
description: Compare two codebases (repos or folders), analyse quality, output the winner.
skills: code-reviewer
---

Compare two repos:
      - Repo 1: $1
      - Repo 2: $2

Explore code in each repo in parallel, and perform review in several dimensions:
      - Clarity: clear goals, directory structure, self-explanatory naming.
      - Architecture: sensible components decomposition, current tech stack, justified complexity.
      - Code quality: minimal tech debt (code smells, antipatterns, temporary/dirty code), code is readable and maintainable.
      - Test coverage: tests for all major pieces of functionality.
      - Completeness: no gaps in implementation, not only success path, but foreseeable failure scenarios, errors and edge cases are properly handled.
      - UX (if applicable): thoughtfulness of UI, ergonomics.

Rate each dimension 0-5 stars. Provide summary table and examples that illustrate the difference between repos. Provide final verdict.
