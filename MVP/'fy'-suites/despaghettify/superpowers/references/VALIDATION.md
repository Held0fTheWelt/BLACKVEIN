# Validating Despaghettify skill paths

## CLI (local / CI)

From the repository root:

```bash
python "./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"
```

Exit **0** if every `](...)` link and every scanned backtick repo path under `'fy'-suites/despaghettify/superpowers/**/*.md` resolves to an existing file (or allowed path under the repo). Exit **1** on any missing target.

## GitHub Actions

Workflow: [`.github/workflows/despaghettify-skills-validate.yml`](../../../../.github/workflows/despaghettify-skills-validate.yml) runs on pushes/PRs that touch `'fy'-suites/despaghettify/superpowers/` or the validator.

## Optional pre-commit

If the repo uses [pre-commit](https://pre-commit.com/), add a **local** hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: validate-despag-skill-paths
        name: validate despaghettify skill paths
        entry: python "./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"
        language: system
        pass_filenames: false
        files: ^despaghettify/superpowers/
```

There is **no** committed `.pre-commit-config.yaml` in this repository by default; copy the snippet into your own config if you use pre-commit.
