# Ubuntu/Debian OpenSSH + UFW + Fail2ban Flow

Use these command patterns after collecting the parameters in `SKILL.md`. Adjust variable values explicitly; do not silently use placeholder values.

## Optional Local Keypair

Use this when the user has no existing SSH key for the server or wants a dedicated per-server key. Recommended naming is the server alias, for example:

```text
~/.ssh/ALIAS
C:\Users\USER\.ssh\ALIAS
```

Do not overwrite existing key files. Check first:

```powershell
Test-Path "IDENTITY_FILE"
Test-Path "IDENTITY_FILE.pub"
```

or on POSIX shells:

```bash
test -e "$IDENTITY_FILE" || test -e "$IDENTITY_FILE.pub"
```

If either file exists, ask the user whether to reuse that key or choose another `local_key_name`.

Generate an ed25519 keypair after the path and passphrase policy are clear:

```powershell
ssh-keygen -t ed25519 -f "IDENTITY_FILE" -C "LOCAL_KEY_COMMENT"
```

For an intentionally empty passphrase, use:

```powershell
ssh-keygen -t ed25519 -f "IDENTITY_FILE" -C "LOCAL_KEY_COMMENT" -N ""
```

Then verify and use the generated public key:

```powershell
ssh-keygen -lf "IDENTITY_FILE.pub"
Get-Content "IDENTITY_FILE.pub"
```

Set:

```text
identity_file = IDENTITY_FILE
public_key_source = IDENTITY_FILE.pub
```

Never print or transmit the private key. Only upload the `.pub` content to the server.

## Root Public-Key Bootstrap

Use this as the default path when the user only has an IP and root password. Do not automate the password login by default. Instead, provide the public key and ask the user to install it once using the provider console, Tabby, VNC, or manual SSH password login.

Show the user this remote command with the actual public key substituted:

```bash
install -d -m 700 -o root -g root /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown root:root /root/.ssh/authorized_keys
grep -qxF 'PUBLIC_KEY_HERE' /root/.ssh/authorized_keys || printf '%s\n' 'PUBLIC_KEY_HERE' >> /root/.ssh/authorized_keys
```

Then verify root public-key login before making any remote changes:

```powershell
ssh -o BatchMode=yes -o PreferredAuthentications=publickey -i "IDENTITY_FILE" -p INITIAL_PORT INITIAL_USER@TARGET_HOST "hostname; id"
```

Expected: the command succeeds and `id` shows the initial user, usually `uid=0(root)`.

If this verification fails, stop. Do not install packages, change SSH configuration, or modify firewall rules.

Password-based bootstrap is an advanced exception. Use it only if the user explicitly asks for it and the available method does not expose the password in command-line arguments, logs, or saved config.

## Input Validation

Validate operator-provided values before substituting them into commands or config files:

```bash
printf '%s\n' "$ADMIN_USER" | grep -Eq '^[a-z_][a-z0-9_-]{0,31}$' || { echo "Invalid ADMIN_USER"; exit 1; }
[ "$ADMIN_USER" != root ] || { echo "ADMIN_USER must not be root"; exit 1; }

case "$INITIAL_PORT" in ''|*[!0-9]*) echo "Invalid INITIAL_PORT"; exit 1;; esac
case "$NEW_SSH_PORT" in ''|*[!0-9]*) echo "Invalid NEW_SSH_PORT"; exit 1;; esac
[ "$INITIAL_PORT" -ge 1 ] && [ "$INITIAL_PORT" -le 65535 ] || { echo "INITIAL_PORT out of range"; exit 1; }
[ "$NEW_SSH_PORT" -ge 1 ] && [ "$NEW_SSH_PORT" -le 65535 ] || { echo "NEW_SSH_PORT out of range"; exit 1; }

case "$TARGET_HOST" in ''|*[!A-Za-z0-9._:-]*) echo "Suspicious TARGET_HOST"; exit 1;; esac

tmp_pub=$(mktemp)
printf '%s\n' "$PUBLIC_KEY" > "$tmp_pub"
[ "$(grep -cve '^[[:space:]]*$' "$tmp_pub")" -eq 1 ] || { rm -f "$tmp_pub"; echo "PUBLIC_KEY must contain exactly one non-empty line"; exit 1; }
key_type=$(awk 'NF { print $1; exit }' "$tmp_pub")
case "$key_type" in
  ssh-ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521|sk-ssh-ed25519@openssh.com|sk-ecdsa-sha2-nistp256@openssh.com) ;;
  ssh-rsa) echo "WARNING: ssh-rsa keys are legacy. Prefer an ed25519 key for new servers." ;;
  *) rm -f "$tmp_pub"; echo "Unsupported PUBLIC_KEY type"; exit 1 ;;
esac
ssh-keygen -lf "$tmp_pub" >/dev/null || { rm -f "$tmp_pub"; echo "Invalid PUBLIC_KEY"; exit 1; }
rm -f "$tmp_pub"
```

If the public key contains unusual quoting characters in its comment, avoid embedding it directly in a shell one-liner. Put it in a temporary file or paste it through the provider console.

## Preflight

Run read-only checks first:

```bash
hostname
date
id
uname -a
command -v sudo || true
command -v ufw || true
command -v fail2ban-client || true
sshd -T | egrep '^(port|permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) '
ss -ltnp | egrep 'ssh|sshd|systemd|:22\b' || true
systemctl is-enabled ssh.socket ssh.service 2>/dev/null || true
systemctl is-active ssh.socket ssh.service 2>/dev/null || true
systemctl cat ssh.socket ssh.service 2>/dev/null || true
ufw status || true
grep -RIn '^[[:space:]]*Match[[:space:]]' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null || true
```

Check current keys:

```bash
ls -ld /root/.ssh /home/*/.ssh 2>/dev/null || true
ls -l /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null || true
```

## Stage 1: Create Verified Admin Path

Install basics:

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y sudo ufw
```

Create the admin user and install a public key:

```bash
if id "$ADMIN_USER" >/dev/null 2>&1; then
  uid=$(id -u "$ADMIN_USER")
  entry=$(getent passwd "$ADMIN_USER")
  home=$(printf '%s\n' "$entry" | cut -d: -f6)
  shell=$(printf '%s\n' "$entry" | cut -d: -f7)
  [ "$uid" -ge 1000 ] || { echo "ERROR: existing ADMIN_USER has system UID"; exit 1; }
  [ -n "$home" ] && [ "$home" != "/" ] && [ -d "$home" ] || { echo "ERROR: existing ADMIN_USER has no usable home directory"; exit 1; }
  case "$shell" in */nologin|*/false|'') echo "ERROR: existing ADMIN_USER has non-interactive shell"; exit 1 ;; esac
  [ ! -f /etc/shells ] || grep -qxF "$shell" /etc/shells || { echo "ERROR: existing ADMIN_USER shell is not listed in /etc/shells"; exit 1; }
  admin_home="$home"
else
  useradd -m -s /bin/bash "$ADMIN_USER"
  admin_home=$(getent passwd "$ADMIN_USER" | cut -d: -f6)
fi
[ -n "$admin_home" ] && [ "$admin_home" != "/" ] || { echo "ERROR: ADMIN_USER has no usable home directory"; exit 1; }
mkdir -p "$admin_home/.ssh"
chmod 700 "$admin_home/.ssh"
touch "$admin_home/.ssh/authorized_keys"
chmod 600 "$admin_home/.ssh/authorized_keys"
chown -R "$ADMIN_USER:" "$admin_home/.ssh"
grep -qxF "$PUBLIC_KEY" "$admin_home/.ssh/authorized_keys" || printf '%s\n' "$PUBLIC_KEY" >> "$admin_home/.ssh/authorized_keys"
```

Configure passwordless sudo:

```bash
printf '%s ALL=(ALL) NOPASSWD: ALL\n' "$ADMIN_USER" > "/etc/sudoers.d/$ADMIN_USER-nopasswd"
chmod 0440 "/etc/sudoers.d/$ADMIN_USER-nopasswd"
visudo -c -f "/etc/sudoers.d/$ADMIN_USER-nopasswd"
```

Back up and add a temporary SSH drop-in that keeps both old and new ports:

```bash
stamp=$(date +%Y%m%d-%H%M%S)
cp -a /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$stamp"
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-bootstrap-ports.conf <<EOF
Port $INITIAL_PORT
Port $NEW_SSH_PORT
PubkeyAuthentication yes
EOF
sshd -t
```

Temporarily allow both ports:

```bash
ufw status numbered || true
if ufw status | grep -q '^Status: active' && ufw status numbered | awk -v old="$INITIAL_PORT" -v new="$NEW_SSH_PORT" '
  /^\[[ 0-9]+\]/ {
    rule=$0
    sub(/^\[[ 0-9]+\][[:space:]]*/, "", rule)
    split(rule, parts, /[[:space:]]+/)
    port=parts[1]
    sub(/\/.*/, "", port)
    if (port == "OpenSSH") next
    if (port != old && port != new && port != "22") found=1
  }
  END { exit found ? 0 : 1 }
'; then
  echo "ERROR: UFW has existing non-SSH rules. Ask the user whether to preserve or migrate them before resetting."
  exit 1
fi
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "$INITIAL_PORT/tcp"
ufw allow "$NEW_SSH_PORT/tcp"
ufw --force enable
if systemctl list-unit-files --type=socket 2>/dev/null | awk '{print $1}' | grep -qx 'ssh.socket'; then
  mkdir -p "/root/ssh-systemd-backup-$stamp"
  systemctl cat ssh.socket ssh.service > "/root/ssh-systemd-backup-$stamp/systemctl-cat-before.txt" 2>/dev/null || true
  systemctl disable --now ssh.socket || true
  if [ -f /etc/systemd/system/ssh.service.d/00-socket.conf ]; then
    cp -a /etc/systemd/system/ssh.service.d/00-socket.conf "/root/ssh-systemd-backup-$stamp/00-socket.conf"
    mv /etc/systemd/system/ssh.service.d/00-socket.conf "/etc/systemd/system/ssh.service.d/00-socket.conf.disabled-by-server-security-init.$stamp"
  fi
  systemctl daemon-reload
fi
systemctl enable --now ssh.service 2>/dev/null || systemctl enable --now ssh 2>/dev/null || true
systemctl restart ssh.service 2>/dev/null || systemctl restart ssh 2>/dev/null || systemctl restart sshd
ss -ltnp | egrep "ssh|sshd|systemd|:$INITIAL_PORT\\b|:$NEW_SSH_PORT\\b" || true
ss -H -ltnp | awk -v port=":$NEW_SSH_PORT" '$4 ~ port "$" && ($0 ~ /sshd/ || $0 ~ /systemd/) { found=1 } END { exit found ? 0 : 1 }' || { echo "ERROR: SSH is not listening on NEW_SSH_PORT via sshd or systemd"; exit 1; }
```

Before continuing, verify from a separate command:

```bash
ssh -p "$NEW_SSH_PORT" "$ADMIN_USER@$TARGET_HOST" "id; sudo -n whoami"
```

Expected: user is `ADMIN_USER`, sudo output is `root`.

## Stage 2: Final SSH and UFW State

Do not run this stage until the new admin path is verified.

Disable earlier active directives in main and drop-in configs before writing the final policy:

```bash
stamp=$(date +%Y%m%d-%H%M%S)
cp -a /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.final.$stamp"
if ls /etc/ssh/sshd_config.d/*.conf >/dev/null 2>&1; then
  mkdir -p "/root/ssh-configd-backup-final-$stamp"
  cp -a /etc/ssh/sshd_config.d/*.conf "/root/ssh-configd-backup-final-$stamp/"
fi

if grep -RIn '^[[:space:]]*Match[[:space:]]' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null; then
  echo "ERROR: SSH Match blocks found. Review conditional policy manually before bulk-commenting directives."
  exit 1
fi

sed -i -E 's/^([[:space:]]*)(Port|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|KbdInteractiveAuthentication|ChallengeResponseAuthentication)([[:space:]].*)/# disabled by server-security-init: \1\2\3/' /etc/ssh/sshd_config
if ls /etc/ssh/sshd_config.d/*.conf >/dev/null 2>&1; then
  sed -i -E 's/^([[:space:]]*)(Port|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|KbdInteractiveAuthentication|ChallengeResponseAuthentication)([[:space:]].*)/# disabled by server-security-init: \1\2\3/' /etc/ssh/sshd_config.d/*.conf
fi

cat > /etc/ssh/sshd_config.d/99-security-init.conf <<EOF
Port $NEW_SSH_PORT
PubkeyAuthentication yes
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
EOF

sshd -t
if systemctl list-unit-files --type=socket 2>/dev/null | awk '{print $1}' | grep -qx 'ssh.socket'; then
  mkdir -p "/root/ssh-systemd-backup-final-$stamp"
  systemctl cat ssh.socket ssh.service > "/root/ssh-systemd-backup-final-$stamp/systemctl-cat-before.txt" 2>/dev/null || true
  systemctl disable --now ssh.socket || true
  if [ -f /etc/systemd/system/ssh.service.d/00-socket.conf ]; then
    cp -a /etc/systemd/system/ssh.service.d/00-socket.conf "/root/ssh-systemd-backup-final-$stamp/00-socket.conf"
    mv /etc/systemd/system/ssh.service.d/00-socket.conf "/etc/systemd/system/ssh.service.d/00-socket.conf.disabled-by-server-security-init.$stamp"
  fi
  systemctl daemon-reload
fi
systemctl enable --now ssh.service 2>/dev/null || systemctl enable --now ssh 2>/dev/null || true
systemctl restart ssh.service 2>/dev/null || systemctl restart ssh 2>/dev/null || systemctl restart sshd
systemctl is-enabled ssh.socket ssh.service 2>/dev/null || true
systemctl is-active ssh.socket ssh.service 2>/dev/null || true
sshd -T | egrep '^(port|permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) '
ss -ltnp | egrep "ssh|sshd|systemd|:$INITIAL_PORT\\b|:$NEW_SSH_PORT\\b" || true
ss -H -ltnp | awk -v port=":$NEW_SSH_PORT" '$4 ~ port "$" && ($0 ~ /sshd/ || $0 ~ /systemd/) { found=1 } END { exit found ? 0 : 1 }' || { echo "ERROR: SSH is not listening on NEW_SSH_PORT via sshd or systemd"; exit 1; }
if [ "$INITIAL_PORT" != "$NEW_SSH_PORT" ] && ss -H -ltnp | awk -v port=":$INITIAL_PORT" '$4 ~ port "$" && ($0 ~ /sshd/ || $0 ~ /systemd/) { found=1 } END { exit found ? 0 : 1 }'; then
  echo "ERROR: old SSH port is still listening"
  exit 1
fi
```

On Debian 12 and similar systemd hosts, `ssh.socket` can keep listening on port 22 even when `sshd_config` says a different `Port`. Treat `ss -ltnp` as the truth. If socket activation is intentionally used instead of `ssh.service`, update the socket unit `ListenStream` values explicitly and verify them with `systemctl cat ssh.socket`.

Before replacing final firewall rules, verify the final admin SSH path again from a separate local command:

```bash
ssh -p "$NEW_SSH_PORT" "$ADMIN_USER@$TARGET_HOST" "id; sudo -n whoami"
```

Expected: user is `ADMIN_USER`, sudo output is `root`.

Set final firewall rules:

```bash
ufw status numbered || true
if ufw status | grep -q '^Status: active' && ufw status numbered | awk -v old="$INITIAL_PORT" -v new="$NEW_SSH_PORT" '
  /^\[[ 0-9]+\]/ {
    rule=$0
    sub(/^\[[ 0-9]+\][[:space:]]*/, "", rule)
    split(rule, parts, /[[:space:]]+/)
    port=parts[1]
    sub(/\/.*/, "", port)
    if (port == "OpenSSH") next
    if (port != old && port != new && port != "22") found=1
  }
  END { exit found ? 0 : 1 }
'; then
  echo "ERROR: UFW has existing non-SSH rules. Ask the user whether to preserve or migrate them before resetting."
  exit 1
fi
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "$NEW_SSH_PORT/tcp"
# Add any explicitly requested service ports here, one per rule.
ufw --force enable
ufw status
```

## Stage 3: Fail2ban

Before enabling fail2ban, build `IGNORE_IPS` from:

- loopback: `127.0.0.1/8 ::1`
- current admin egress IP
- usual jump hosts or proxy/VPS exits used for management

Install and configure:

```bash
apt-get install -y fail2ban
mkdir -p /etc/fail2ban/jail.d
if [ -f /etc/fail2ban/jail.d/sshd.local ]; then
  cp -a /etc/fail2ban/jail.d/sshd.local "/etc/fail2ban/jail.d/sshd.local.bak.$(date +%Y%m%d-%H%M%S)"
fi

cat > /etc/fail2ban/jail.d/sshd.local <<EOF
[DEFAULT]
ignoreip = $IGNORE_IPS
banaction = ufw

[sshd]
enabled = true
backend = systemd
port = $NEW_SSH_PORT
maxretry = $FAIL2BAN_MAXRETRY
findtime = $FAIL2BAN_FINDTIME
bantime = $FAIL2BAN_BANTIME
EOF

systemctl enable --now fail2ban
systemctl restart fail2ban
fail2ban-client status sshd
fail2ban-client get sshd ignoreip
```

If a management IP is banned:

```bash
fail2ban-client set sshd unbanip "$MANAGEMENT_IP"
```

Then fix `ignoreip` and restart fail2ban.

## Local SSH Config Update

Before editing `~/.ssh/config`, copy it to a timestamped backup. Replace only the matching host block or append a new block if none exists:

```sshconfig
Host ALIAS
  HostName TARGET_HOST
  User ADMIN_USER
  Port NEW_SSH_PORT
  IdentityFile IDENTITY_FILE
```

Verify:

```powershell
ssh -G ALIAS | Select-String -Pattern '^(hostname|user|port|identityfile) '
```

Avoid broad regular expressions that can consume following `Host` blocks.

## TUN/Fake-IP Note

When Clash/Mihomo TUN or fake-IP DNS is enabled, local `ping` and `Test-NetConnection` can report misleading success through the virtual interface. Prefer server-side checks:

```bash
ss -ltnp | egrep 'ssh|sshd|systemd'
sshd -T | egrep '^(port|permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) '
ufw status
```
