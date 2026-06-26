---
name: server-security-init
description: "Use when configuring a newly installed or rebuilt Ubuntu/Debian server over SSH, especially when selecting or generating SSH keys, creating a non-root sudo user, changing SSH ports, disabling root/password login, enabling UFW or fail2ban, updating SSH config, or verifying that the operator is not locked out."
---

# Server Security Init

## Purpose

Use this skill to harden a fresh SSH server without locking the user out. Treat SSH, firewall, and fail2ban changes as high-risk operations that require staged verification.

This skill is intended for Ubuntu/Debian systems using OpenSSH, systemd, UFW, and fail2ban. For other distributions or firewalls, adapt carefully and state the differences before changing anything.

## Required Inputs

Collect or infer these before making changes. If any value is ambiguous, ask before proceeding. For a fresh server request, ask for the bootstrap facts first instead of starting remote commands immediately.

| Parameter | Meaning |
| --- | --- |
| `root_public_key_installed` | Whether the chosen SSH public key has already been installed for the initial server login user |
| `target_host` | IP address or existing SSH alias for the server |
| `initial_user` | Current login user, often `root` |
| `initial_port` | Current SSH port, often `22` |
| `admin_user` | Non-root sudo user to create |
| `public_key_source` | Existing remote authorized key, local `.pub` file, or pasted public key |
| `local_key_name` | Local key basename or server alias to use when selecting or generating a dedicated key |
| `identity_file` | Local private key path for future SSH config |
| `new_ssh_port` | Final SSH port |
| `ssh_config_alias` | Local SSH config alias to create/update |
| `management_ips` | Current and common admin egress IPs or jump hosts to whitelist in fail2ban |

Optional settings:

| Parameter | Default |
| --- | --- |
| `disable_root_login` | `true` |
| `disable_password_login` | `true` |
| `enable_ufw` | `true` |
| `allowed_tcp_ports` | only `new_ssh_port` |
| `enable_fail2ban` | ask or use user preference |
| `fail2ban_maxretry` | `3` |
| `fail2ban_findtime` | `86400` |
| `fail2ban_bantime` | `86400` |
| `generate_local_keypair` | ask during intake if no usable key exists |
| `local_key_comment` | `local_key_name` or user-specified comment |
| `local_key_passphrase` | ask; do not assume empty passphrase unless user prefers automation |

## Input Validation

Validate values before substituting them into shell commands or config files:

- `admin_user`: must be a normal Linux username such as `^[a-z_][a-z0-9_-]{0,31}$`; reject `root`, empty values, whitespace, shell metacharacters, path separators, and newline characters. If the account already exists, stop unless it is clearly an intended human admin account with UID >= 1000, a real home directory, and an interactive shell; never grant passwordless sudo to service/system accounts.
- `initial_port`, `new_ssh_port`, and `allowed_tcp_ports`: must be numeric TCP ports in `1..65535`; prefer unprivileged ports `1024..65535` unless the user explicitly chooses a privileged port.
- `public_key_source` or `public_key_content`: must resolve to exactly one valid non-empty SSH public key line. Verify with `ssh-keygen -lf` against a temporary public-key file and never print private key material.
- `target_host`, `ssh_config_alias`, and `identity_file`: must not contain newline characters. Treat paths and aliases as data, not shell fragments.
- `management_ips`: must contain only explicit IPs or CIDR ranges that the user recognizes. If the current egress IP cannot be determined confidently, ask before enabling fail2ban.

## Safety Rules

- Do not disable root login, password login, the old SSH port, or the old firewall rule until `admin_user@new_ssh_port` has been verified in a separate SSH command.
- Keep an existing working SSH session open while changing SSH or firewall configuration.
- Back up files before editing: `/etc/ssh/sshd_config`, relevant `/etc/ssh/sshd_config.d/*.conf`, fail2ban jail files, and local `~/.ssh/config`.
- Prefer drop-in files for new SSH/fail2ban policy, but ensure earlier directives cannot override the intended final state. Verify with `sshd -T`.
- On systemd hosts, check `ssh.socket` before and after changing SSH ports. If socket activation is enabled, systemd may own the listening port and ignore `Port` values in `sshd_config`; prefer disabling `ssh.socket` and running the traditional `ssh.service` unless intentionally managing socket units.
- Use server-side truth for port/firewall verification: `ss -ltnp`, `sshd -T`, `systemctl status ssh.socket ssh.service`, and `ufw status`. Listener checks must include `systemd` as well as `sshd`; socket activation can make PID 1 own the old port. Local tests can be misleading under Clash/Mihomo TUN or fake-IP DNS.
- Configure fail2ban `ignoreip` before or while enabling fail2ban. Include the current admin egress IP and any usual jump/VPS exits.
- If connectivity is lost, stop changing configuration and recover through an alternate egress, console, rescue panel, or provider VNC before continuing.
- When updating local SSH config, make a backup and replace only the target host block. Do not use broad regexes that can consume following `Host` blocks.
- Do not bake personal defaults into this skill or its examples. Use placeholders such as `<server_alias>`, `<server_ip>`, `<admin_user>`, `<new_ssh_port>`, and `<public_key_content>`.
- When generating a local keypair, never overwrite an existing private key. If `identity_file` or `identity_file.pub` already exists, stop and ask whether to reuse it or choose another name.
- If the user only has an IP and root password, do not use password automation by default. Generate or select a public key, give the user a minimal command to install it under `/root/.ssh/authorized_keys`, and wait until root public-key login is verified.
- Do not place root passwords in shell commands, SSH config, scripts, logs, or final answers. Password-based bootstrap is an advanced exception only when the user explicitly requests it and the environment has a safe non-interactive method.
- If existing SSH config contains `Match` blocks or other non-stock policy, stop before bulk-commenting directives and explain the risk. Conditional `Match` policy can change effective authentication for specific users or source addresses.
- If `admin_user` already exists, inspect it before writing sudoers or SSH keys. Stop on system users, service users, missing home directories, or non-interactive shells unless the user provides an explicit migration plan.
- If UFW is already active with non-SSH rules, do not reset it without explicit user confirmation and a migration plan for existing service ports.

## Workflow

0. **Stage -2: intake gate**
   - When the user asks to initialize or harden a server, ask for these values before touching the server:
     - Whether the SSH public key has already been installed for the initial login user.
     - Server IP or HostName.
     - Initial SSH user and port.
     - Local SSH config alias and local key name.
     - Non-root passwordless sudo username to create.
     - Final SSH port.
     - Whether to enable UFW and fail2ban.
     - Management IPs or other jump/server IPs to add to fail2ban `ignoreip`.
   - If values are inferable from existing SSH config or prior context, state the inferred values and ask for confirmation before high-risk changes.
   - If the public key is not installed yet, do not attempt remote initialization. Move to the key bootstrap gate.

1. **Stage -1: key selection or generation**
   - Use this when the user has no existing key, wants a dedicated per-server key, or has not installed a key on the server yet.
   - Read `references/ubuntu-openssh-ufw-fail2ban.md` for local `ssh-keygen` command patterns.
   - Generate an ed25519 key at the user-specified `identity_file` only after confirming the key name and path.
   - Set `public_key_source` to the generated `.pub` file.
   - Show the public-key fingerprint, not the private key.
   - Use placeholder examples in instructions, for example:

     ```bash
     ssh-keygen -t ed25519 -f ~/.ssh/<server_alias> -C "<server_alias>"
     ```

2. **Stage 0: public-key bootstrap gate**
   - If root public-key login is not already available, instruct the user to install `public_key_source` into `/root/.ssh/authorized_keys` through provider console, Tabby, VNC, or a one-time manual SSH password login.
   - Give the user generic server-side commands for the initial login user. For `root`, use:

     ```bash
     install -d -m 700 -o root -g root /root/.ssh
     touch /root/.ssh/authorized_keys
     chmod 600 /root/.ssh/authorized_keys
     chown root:root /root/.ssh/authorized_keys
     grep -qxF '<public_key_content>' /root/.ssh/authorized_keys || printf '%s\n' '<public_key_content>' >> /root/.ssh/authorized_keys
     ```

   - If the initial login user is not `root`, adjust the home directory and ownership for that user.
   - Do not proceed to remote initialization until `initial_user@target_host:initial_port` works with public-key authentication and `BatchMode=yes`.

3. **Preflight**
   - Confirm reachable public-key login path and gather system facts.
   - Inspect effective SSH settings, systemd `ssh.socket`/`ssh.service` state, listeners, firewall state, and current authorized keys.
   - Determine current admin egress IP from server logs or an external IP service.
   - Validate all collected inputs before using them in commands.

4. **Stage 1: add the new safe path**
   - Install `sudo` and `ufw` if needed.
   - Create `admin_user`, or verify an existing `admin_user` is a normal human admin account before changing its keys or sudo privileges.
   - Install the selected public key for `admin_user`.
   - Configure passwordless sudo for `admin_user` and validate with `visudo`.
   - Configure SSH to listen on both `initial_port` and `new_ssh_port`.
   - Configure UFW to allow both ports temporarily.
   - If `ssh.socket` exists and is active/enabled, disable it, remove or back up socket-related `ssh.service` drop-ins if present, run `systemctl daemon-reload`, and enable the traditional SSH service before relying on `sshd_config` ports.
   - Restart SSH and verify the real listener with `ss -ltnp` including `systemd` and `sshd`, then verify `admin_user@new_ssh_port` plus `sudo -n whoami`.

5. **Stage 2: harden the final state**
   - Set final SSH policy: `Port new_ssh_port`, `PubkeyAuthentication yes`, `PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`.
   - Validate with `sshd -t`, verify effective policy with `sshd -T` and `sshd -T -C` where source/user context matters, ensure `ssh.socket` cannot re-own the old port after reboot, then restart SSH and re-verify `admin_user@new_ssh_port` before changing final firewall rules.
   - Reset UFW to default deny incoming, default allow outgoing, and allow only required ports.
   - Verify with `ss -ltnp` that SSH listens on `new_ssh_port` and not the old port, then verify root login is refused and password login is refused.

6. **Stage 3: fail2ban**
   - Read `references/ubuntu-openssh-ufw-fail2ban.md` before enabling fail2ban.
   - Configure the `sshd` jail with `backend = systemd`, `port = new_ssh_port`, and `banaction = ufw`.
   - Include `management_ips` in `ignoreip`.
   - Restart fail2ban and verify its ban list. If a management IP is banned, unban it immediately and fix `ignoreip`.

7. **Stage 4: local SSH config**
   - Back up the local SSH config.
   - Update or create only `ssh_config_alias` with the final host, user, port, and identity file.
   - Verify with `ssh -G ssh_config_alias`.

8. **Final verification**
   - Read and follow `references/verification-checklist.md`.
   - Report the exact commands run and the meaningful outputs.

## Reference Files

- `references/ubuntu-openssh-ufw-fail2ban.md`: staged Ubuntu/Debian command patterns and recovery notes.
- `references/verification-checklist.md`: final test commands and expected results.
