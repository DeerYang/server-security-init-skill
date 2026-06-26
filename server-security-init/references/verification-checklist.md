# Verification Checklist

Run these after hardening. Report concise command output to the user.

## Local Keypair

If a local keypair was generated, verify the private key and public key exist and report only the public fingerprint:

```powershell
Test-Path "IDENTITY_FILE"
Test-Path "IDENTITY_FILE.pub"
ssh-keygen -lf "IDENTITY_FILE.pub"
```

Expected:

```text
True
True
256 SHA256:... LOCAL_KEY_COMMENT (ED25519)
```

Do not display the private key.

## Initial Root Public-Key Login

Before any remote hardening, verify that the initial root or bootstrap user can be reached with public-key auth:

```powershell
ssh -o BatchMode=yes -o PreferredAuthentications=publickey -i "IDENTITY_FILE" -p INITIAL_PORT INITIAL_USER@TARGET_HOST "hostname; id"
```

Expected for a typical root bootstrap:

```text
HOSTNAME
uid=0(root) gid=0(root) groups=0(root)
```

If this fails, the initialization should not continue.

## SSH Alias

```powershell
ssh -G ALIAS | Select-String -Pattern '^(hostname|user|port|identityfile) '
```

Expected:

```text
user ADMIN_USER
hostname TARGET_HOST
port NEW_SSH_PORT
identityfile IDENTITY_FILE
```

## Admin Login and Sudo

```powershell
ssh ALIAS "hostname; id; sudo -n whoami"
```

Expected:

```text
HOSTNAME
uid=... (ADMIN_USER) ...
root
```

## Effective SSH Policy

```powershell
ssh ALIAS "sudo sshd -T | egrep '^(port|permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) '"
```

Expected:

```text
port NEW_SSH_PORT
permitrootlogin no
pubkeyauthentication yes
passwordauthentication no
kbdinteractiveauthentication no
```

If the server has non-default conditional SSH policy, also check the user/source-specific effective policy:

```powershell
ssh ALIAS "sudo sshd -T -C user=ADMIN_USER,host=TARGET_HOST,addr=MANAGEMENT_IP | egrep '^(port|permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) '"
```

## SSH Systemd Socket State

```powershell
ssh ALIAS "systemctl is-enabled ssh.socket ssh.service 2>/dev/null || true; systemctl is-active ssh.socket ssh.service 2>/dev/null || true; systemctl cat ssh.socket ssh.service 2>/dev/null || true"
```

Expected when using traditional `ssh.service`: `ssh.socket` is disabled or not found, and `ssh.service` is enabled/active. If `ssh.socket` is active, verify its `ListenStream` values match the intended SSH port; otherwise it may keep listening on the old port after reboot.

## SSH Listener

```powershell
ssh ALIAS "sudo ss -ltnp | egrep 'ssh|sshd|systemd|:NEW_SSH_PORT\b|:INITIAL_PORT\b'"
```

Expected: SSH listens on `NEW_SSH_PORT` for IPv4 and/or IPv6, and the listener line is owned by `sshd` or by `systemd` through the intended `ssh.socket`. It must not listen on the old port unless intentionally retained. If `systemd` owns an unexpected SSH port, check `ssh.socket`.

Explicit old-port assertion when the old and new ports differ:

```powershell
ssh ALIAS "if [ INITIAL_PORT != NEW_SSH_PORT ] && sudo ss -H -ltnp | grep -Eq '(^|[[:space:]])[^[:space:]]*:INITIAL_PORT[[:space:]]+.*(sshd|systemd)'; then echo 'ERROR old SSH port still listening through sshd or systemd'; exit 1; else echo 'old SSH port check passed'; fi"
```

## Root Login Refusal

```powershell
ssh -o BatchMode=yes -o PreferredAuthentications=publickey -i "IDENTITY_FILE" -p NEW_SSH_PORT root@TARGET_HOST "true"
```

Expected: command fails with a message like:

```text
Permission denied (publickey).
```

## Password Login Refusal

```powershell
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o BatchMode=yes -p NEW_SSH_PORT ADMIN_USER@TARGET_HOST "true"
```

Expected: command fails with a message like:

```text
Permission denied (publickey).
```

Treat this as a smoke test only. The stronger proof is the server-side effective policy showing both password and keyboard-interactive authentication are disabled.

## UFW

```powershell
ssh ALIAS "sudo ufw status"
```

Expected:

```text
Status: active
NEW_SSH_PORT/tcp ALLOW Anywhere
```

Other allowed ports should be only those the user explicitly requested.

## Fail2ban

```powershell
ssh ALIAS "sudo fail2ban-client status; sudo fail2ban-client status sshd; sudo fail2ban-client get sshd ignoreip"
```

Expected:

```text
Jail list: sshd
Status for the jail: sshd
```

Check that management IPs appear in `ignoreip` and are not in `Banned IP list`.

## Recovery Checks

If the user cannot connect from a usual route:

```bash
systemctl status ssh.socket ssh.service --no-pager -l
ss -ltnp | egrep 'ssh|sshd|systemd'
fail2ban-client status sshd
ufw status numbered
journalctl _COMM=sshd --since "today" --no-pager | tail -n 100
tail -n 100 /var/log/fail2ban.log
```

If a management IP is accidentally banned:

```bash
fail2ban-client set sshd unbanip IP_ADDRESS
```

Then add it to `ignoreip` and restart fail2ban.
