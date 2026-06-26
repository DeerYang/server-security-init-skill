# Security Policy

## Supported Scope

This repository provides an Agent Skill and reference commands for hardening fresh Ubuntu/Debian SSH servers. It is not an automated security product and does not guarantee server safety.

## Reporting Security Issues

If you find an unsafe instruction, a lockout risk, a secret-handling issue, or a command sequence that can weaken a server, open a private security advisory if the hosting platform supports it. Otherwise, open an issue with enough detail to reproduce the problem without including secrets.

## Do Not Include Secrets

Never include these in issues, pull requests, screenshots, logs, examples, or test fixtures:

- Private SSH keys.
- Root or user passwords.
- API tokens, provider tokens, or recovery codes.
- Real server IP addresses if they are not intentionally public.
- Real SSH aliases, usernames, hostnames, domains, or management IPs tied to a private deployment.

Use placeholders such as `TARGET_HOST`, `ADMIN_USER`, `NEW_SSH_PORT`, `IDENTITY_FILE`, and `PUBLIC_KEY_HERE`.

## Operational Safety

SSH and firewall hardening can lock operators out. Changes to this repository should preserve these invariants:

- Verify public-key login before changing remote access policy.
- Verify the new non-root sudo path before disabling root login, password login, the old SSH port, or old firewall rules.
- Back up modified remote configuration files.
- Verify real listeners with `ss -ltnp`, not only `sshd -T`.
- Check systemd `ssh.socket` on Debian 12 and similar systems before trusting SSH port changes.
- Include current management IPs in fail2ban `ignoreip` before enabling or restarting fail2ban.
