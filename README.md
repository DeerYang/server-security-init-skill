# Server Security Init Skill

[English](README.md) | [简体中文](README.zh-CN.md)

An Agent Skill for safely initializing and hardening fresh Ubuntu/Debian SSH servers.

The skill guides an agent through a staged server bootstrap flow: selecting or generating a local SSH key, requiring public-key login before remote changes, creating a non-root sudo user, changing the SSH port, disabling root/password login, configuring UFW, configuring fail2ban, updating local SSH config, and verifying the operator is not locked out.

## What It Covers

- Public-key bootstrap without putting root passwords into commands, logs, or config files.
- Staged SSH hardening with a verified non-root sudo login before disabling old access paths.
- UFW default-deny inbound policy with only explicitly requested ports allowed.
- Fail2ban `sshd` jail setup with management IPs in `ignoreip`.
- Debian 12/systemd `ssh.socket` checks so socket activation does not silently keep SSH on the old port.
- Verification commands that prefer server-side truth such as `ss -ltnp`, `sshd -T`, `systemctl`, and `ufw status`.
- Recovery checks for fail2ban bans, firewall mistakes, and SSH listener mismatches.

## Repository Layout

```text
server-security-init-skill/
  server-security-init/
    SKILL.md
    agents/openai.yaml
    references/
      ubuntu-openssh-ufw-fail2ban.md
      verification-checklist.md
  scripts/
    validate_skill.py
  .github/workflows/validate.yml
  README.md
  README.zh-CN.md
  LICENSE
  SECURITY.md
```

The installable skill is the `server-security-init/` directory. The repository-level files are for humans, validation, and open-source maintenance.

## For AI Agents

Install only the `server-security-init/` directory as the skill.

Do not install the repository root as a skill. Do not run server initialization during installation.

After installation, tell the user whether their current agent needs to restart, reload, or refresh skills.

## For Humans

Clone or download this repository:

```bash
git clone https://github.com/DeerYang/server-security-init-skill.git
```

Then copy only the `server-security-init/` directory into your AI agent's user-level skills directory.

Restart or reload your AI agent if it does not detect new skills automatically.

## Optional: Install with npx

If you have Node.js/npm installed, you can install the skill with the `skills` CLI:

```bash
npx skills add https://github.com/DeerYang/server-security-init-skill/tree/main/server-security-init -g
```

To target a specific supported agent:

```bash
npx skills add https://github.com/DeerYang/server-security-init-skill/tree/main/server-security-init -g -a codex
npx skills add https://github.com/DeerYang/server-security-init-skill/tree/main/server-security-init -g -a claude-code
```

Without `-g`, the CLI may install the skill into the current project's skill directory instead of the user-level directory.

## Usage

Ask your AI agent to use the skill when initializing a fresh server, for example:

```text
Use server-security-init to initialize my new Ubuntu server.
```

The skill is intentionally conservative. It should ask for bootstrap facts before touching the server and should stop if public-key SSH login cannot be verified.

## Safety Notes

- Review the generated commands before running them on production systems.
- Keep an existing working SSH session open while changing SSH or firewall settings.
- Do not paste private keys or root passwords into prompts, scripts, command lines, or repository files.
- Provider consoles, rescue panels, and VNC access are still required recovery paths for mistakes outside SSH reachability.
- This project is guidance for AI-assisted administration, not a substitute for understanding the commands being run.

## Validation

Run the repository validator before publishing changes:

```bash
python scripts/validate_skill.py
```

The validator checks required files, frontmatter, and common secret/personal-data patterns.

## Supported Targets

This skill is written for Ubuntu/Debian systems using OpenSSH, systemd, UFW, and fail2ban. Other distributions, firewall systems, init systems, and SSH implementations need careful adaptation.

## Friendly Links

- [LINUX DO](https://linux.do)

## License

MIT License. See [LICENSE](LICENSE).
