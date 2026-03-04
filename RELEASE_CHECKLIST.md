# Release Checklist

## Pre-Release

- [ ] Update `VERSION` (e.g. `1.0.1`)
- [ ] Verify UI language switch (EN/DE)
- [ ] Run local app once: `python main.py`
- [ ] Run syntax check: `python -m py_compile main.py`
- [ ] Build portable EXE: `.\scripts\build_exe.ps1`
- [ ] Build installer: `.\scripts\build_installer.ps1`
- [ ] Run installer smoke test: `.\scripts\test_installer.ps1 -SkipBuild`
- [ ] Verify release artifacts in `dist-installer\`
- [ ] Review `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`

## GitHub Publish

- [ ] Commit all changes
- [ ] Push branch
- [ ] Create and push tag:
  - `git tag v<version>`
  - `git push origin v<version>`
- [ ] Wait for GitHub Actions workflow (`windows-release.yml`)
- [ ] Validate uploaded release assets (`Setup.exe`, `Portable.zip`)

## Post-Release

- [ ] Install setup on clean machine (or VM) and smoke test
- [ ] Confirm uninstall entry in Windows settings
- [ ] Confirm uninstall keep/delete behavior for `%APPDATA%\FFmpeg-Konverter`
