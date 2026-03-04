# Security Notes

## EN

- Never commit API tokens, PATs, passwords, or private keys to the repository.
- If a token was exposed, revoke and rotate it immediately.
- Use repository secrets for CI/CD (`Settings -> Secrets`).
- Prefer least-privilege tokens (only required scopes).

## DE

- Keine API-Tokens, PATs, Passwörter oder privaten Schlüssel ins Repository committen.
- Wenn ein Token offengelegt wurde, sofort widerrufen und neu erstellen.
- Für CI/CD immer Repository-Secrets nutzen (`Settings -> Secrets`).
- Tokens mit minimalen Rechten verwenden (Least Privilege).
