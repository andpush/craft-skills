---
name: fix
description: Use to perform surgical quick fix.
---
1. Understand the problem, ask user questions to reach shared understanding.
2. Ensure the problem is real, and the fix will not spawn more problems.
3. Explore the repo, find root cause.
4. Write test case against the proper behavior, execute to ensure it is red.
5. Implement code fix, ensure that you (a) follow architecture and adopted conventions; (b) the fix belongs to the right abstraction level; (c) the fix is surgically minimal and it causes no undesirable side effects.
6. Acceptance: Build and run test suite to ensure all green.