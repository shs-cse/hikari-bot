## How to update [`info.jsonc`](./info.jsonc) file pattern in `git`
- Don't track changes in the file:
    ```bash
    git update-index --skip-worktree info.jsonc
    ```
- Track changes in the file again:
    ```bash
    git update-index --no-skip-worktree info.jsonc