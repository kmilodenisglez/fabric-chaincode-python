# Releasing fabric-chaincode-python

This document describes the release process for the `fabric-chaincode-python` package.

## Release Strategy

The project uses a **main + release branch** model:

- **`main`** — Development branch with latest features and fixes
- **`release-2.5`** — Release maintenance branch for v2.5.x patch releases
- **Tags** — Git tags (e.g., `v2.5.0`, `v2.5.1`) trigger automated wheel builds and optional PyPI publishing

## Making a Release

### Prerequisites

1. Ensure you have push access to the repository
2. All commits must be signed off with DCO (`-s` flag in git commit)
3. Tests must pass locally:
   ```bash
   pytest -v
   ```

### Step-by-Step Release Process

#### 1. Prepare on `main`

Make any necessary changes on `main` (bug fixes, version bumps, documentation):

```bash
git checkout main
git pull origin main
# Make your changes...
git add .
git commit -s -m "fix: description of fix" 
git push origin main
```

#### 2. Sync `release-2.5` from `main`

```bash
git checkout release-2.5
git pull origin main
git push origin release-2.5
```

#### 3. Create the Release Tag

From `release-2.5`, create an annotated tag (recommended for releases):

```bash
COMMIT=$(git rev-parse release-2.5)
git tag -a v2.5.X -m "Release v2.5.X - Description" "$COMMIT"
git push origin v2.5.X
```

Replace `X` with the patch version number (e.g., `v2.5.1`, `v2.5.2`, etc.).

#### 4. Monitor the Workflow

The tag push automatically triggers the release workflow (`.github/workflows/release.yml`):

```bash
gh run list --repo kmilodenisglez/fabric-chaincode-python --workflow release.yml --limit 5
```

Expected workflow steps:
1. ✅ Checkout repository
2. ✅ Set up Python 3.11
3. ✅ Install build dependencies
4. ✅ Build wheel
5. ✅ Upload wheel artifact
6. 📤 (Optional) Publish to PyPI (if `PYPI_API_TOKEN` is configured)

### Verifying the Release

#### Check Workflow Status

```bash
gh run view <RUN_ID> --repo kmilodenisglez/fabric-chaincode-python --log
```

#### Access the Wheel Artifact

Artifacts are available in GitHub Actions run details:
1. Visit: https://github.com/kmilodenisglez/fabric-chaincode-python/actions
2. Click the successful release run (tagged with `v2.5.X`)
3. Download the `wheel` artifact (contains `.whl` file)

#### Test the Wheel Locally

```bash
pip install dist/fabric-chaincode-python-*.whl
python -c "import src.fabric_shim; print('✓ Package imported successfully')"
```

## PyPI Publishing (Optional)

### Setup (One-Time)

To enable automatic PyPI publishing on releases:

#### 1. Create a PyPI Account
- Go to https://pypi.org/account/register/
- Create an account or use existing credentials

#### 2. Generate an API Token
- Log into PyPI
- Navigate to Account → API Tokens
- Create a new token with "Entire repository" scope
- Copy the token (starts with `pypi-`)

#### 3. Add GitHub Secret

```bash
gh secret set PYPI_API_TOKEN --repo kmilodenisglez/fabric-chaincode-python
# Paste the token when prompted
```

Verify the secret is set:
```bash
gh secret list --repo kmilodenisglez/fabric-chaincode-python
```

### Publishing Process

Once the PyPI token is configured, releases automatically:
1. Build the wheel
2. Attempt to publish to PyPI (continues on error if token is invalid/missing)

You can also manually publish a built wheel:

```bash
pip install twine
python -m twine upload dist/fabric-chaincode-python-*.whl -u __token__ -p $PYPI_API_TOKEN
```

## Troubleshooting

### Build Fails in Workflow

Check the workflow logs:
```bash
gh run view <RUN_ID> --repo kmilodenisglez/fabric-chaincode-python --log
```

Common issues:
- **Missing dependencies**: Ensure `requirements.txt` and `pyproject.toml` are in sync
- **Import errors**: Verify `setup.py` correctly loads the version without importing the package
- **YAML syntax errors**: Validate `.github/workflows/release.yml` with `yamllint`

### PyPI Publish Fails

- Verify the token is valid (check GitHub secrets)
- Ensure the version number is unique (PyPI doesn't allow re-uploading the same version)
- For test uploads, use TestPyPI: https://test.pypi.org/

## Release Checklist

- [ ] All commits signed off (`-s` flag)
- [ ] Tests pass locally (`pytest -v`)
- [ ] CHANGELOG updated (if applicable)
- [ ] Version bumped in `src/version.py` (if applicable)
- [ ] `release-2.5` synced from `main`
- [ ] Release tag created (`v2.5.X`)
- [ ] Workflow run successful
- [ ] Wheel artifact downloaded and tested locally
- [ ] PyPI publish successful (if enabled)

## Rollback

If a release needs to be rolled back:

```bash
# Delete the tag locally and remotely
git tag -d v2.5.X
git push origin --delete v2.5.X

# The workflow run cannot be undone, but the PyPI publish can be manually removed
# by deleting the release on PyPI if necessary
```

## References

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI API Tokens](https://pypi.org/help/#apitoken)
- [GitHub Actions](https://github.com/features/actions)
- [DCO Sign-off](https://probot.github.io/apps/dco/)
