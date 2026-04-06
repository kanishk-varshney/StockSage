# History rewrite checklist

If maintainers perform a full history rewrite (secret/artifact purge), collaborators should:

1. Save local work (`git stash` or local patch) before syncing.
2. Re-clone the repository, or hard-reset local `main` to the new remote tip.
3. Prune stale refs:
   ```bash
   git fetch --all --prune
   ```
4. Delete old local branches based on pre-rewrite commits.
5. Regenerate local environment:
   ```bash
   uv sync --extra dev
   ```

For open PRs based on old history, recreate the branch from the new `main` and reapply changes.
