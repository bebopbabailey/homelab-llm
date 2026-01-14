# Git Submodules in IntelliJ

This repo uses submodules for active services. The safe workflow is always:
1) Commit inside the submodule
2) Then commit the updated submodule pointer in the monorepo

## Clone + init
- **Get from VCS** → clone the monorepo
- In the terminal (IntelliJ or system):
  ```bash
  git submodule update --init --recursive
  ```

## Working inside a submodule
1) Open the submodule folder as a project **or** use the Project tool window.
2) Make changes in the submodule.
3) Commit:
   - VCS → Commit
   - Ensure the commit is in the submodule repo (check the commit dialog path).
4) Push the submodule:
   - VCS → Git → Push

## Update the monorepo pointer
1) Switch back to the monorepo project.
2) The submodule will appear as modified.
3) Commit the pointer:
   - VCS → Commit (monorepo)
   - Commit message example: `Update <service> submodule`
4) Push the monorepo.

## Common pitfalls
- Editing submodule files but committing in the monorepo (wrong repo).
- Forgetting to commit the submodule pointer in the monorepo.
- Pulling monorepo updates without `git submodule update`.

## Quick check
```bash
git submodule status
```
If you see a leading `-` or `+`, run:
```bash
git submodule update --init --recursive
```
