---
name: fix
description: Use to perform surgical quick fix.
---
1. Understand the problem, ask user questions if more details needed. Validate that it is indeed a problem, not work as designed.
2. Explore the repo to find the root cause.
3. Write test case against the proper behavior, execute to ensure it is red.
4. Implement code fix, ensure that you (a) follow architecture and adopted conventions; (b) the fix belongs to the right abstraction level.
5. Build and run test suite to ensure all green.