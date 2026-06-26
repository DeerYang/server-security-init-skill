# Server Security Init Skill

[English](README.md) | [简体中文](README.zh-CN.md)

一个用于安全初始化和加固全新 Ubuntu/Debian SSH 服务器的 Agent Skill。

这个 skill 会引导 AI agent 按阶段完成服务器初始化流程：选择或生成本地 SSH 密钥、在远程修改前确认公钥登录可用、创建非 root sudo 用户、修改 SSH 端口、禁用 root 登录和密码登录、配置 UFW、配置 fail2ban、更新本地 SSH config，并验证操作者不会被锁在服务器外。

## 覆盖内容

- 使用公钥完成初始引导，避免把 root 密码写入命令、日志或配置文件。
- 分阶段进行 SSH 加固，在禁用旧登录路径前先验证非 root sudo 用户可以登录。
- 配置 UFW 默认拒绝入站连接，只放行明确需要的端口。
- 配置 fail2ban `sshd` jail，并把管理 IP 加入 `ignoreip`。
- 检查 Debian 12/systemd 的 `ssh.socket`，避免 socket activation 悄悄让 SSH 继续监听旧端口。
- 优先使用服务器侧真实状态进行验证，例如 `ss -ltnp`、`sshd -T`、`systemctl` 和 `ufw status`。
- 提供 fail2ban 封禁、防火墙配置错误、SSH 监听端口不一致等问题的恢复检查。

## 仓库结构

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

真正可安装的 skill 是 `server-security-init/` 目录。仓库根目录下的其他文件用于人工阅读、校验和开源维护。

## 给 AI Agents

只安装 `server-security-init/` 目录作为 skill。

不要把仓库根目录作为 skill 安装。安装期间不要执行服务器初始化，也不要修改任何服务器。

安装完成后，告诉用户当前 agent 是否需要重启、重新加载或刷新 skills。

## 给人工用户

克隆或下载这个仓库：

```bash
git clone https://github.com/DeerYang/server-security-init-skill.git
```

然后只复制 `server-security-init/` 目录到你的 AI agent 的用户级 skills 目录。

如果你的 AI agent 没有自动检测到新 skill，请重启或重新加载 agent。

## 可选：使用 npx 安装

如果你已经安装 Node.js/npm，可以用 `skills` CLI 安装：

```bash
npx skills add https://github.com/DeerYang/server-security-init-skill/tree/main/server-security-init -g
```

指定某个受支持的 agent：

```bash
npx skills add https://github.com/DeerYang/server-security-init-skill/tree/main/server-security-init -g -a codex
npx skills add https://github.com/DeerYang/server-security-init-skill/tree/main/server-security-init -g -a claude-code
```

如果不加 `-g`，CLI 可能会把 skill 安装到当前项目的 skill 目录，而不是用户级目录。

## 使用方式

在初始化新服务器时，让你的 AI agent 使用这个 skill，例如：

```text
Use server-security-init to initialize my new Ubuntu server.
```

这个 skill 会刻意保持保守。它应该先询问初始化所需的信息，再接触服务器；如果不能验证公钥 SSH 登录可用，它应该停止继续操作。

## 安全说明

- 在生产系统上运行前，先审查 agent 生成的命令。
- 修改 SSH 或防火墙配置时，保留一个已经可用的 SSH 会话，不要提前关闭。
- 不要把私钥或 root 密码粘贴到提示词、脚本、命令行或仓库文件里。
- 云厂商控制台、救援面板和 VNC 仍然是 SSH 不可达时需要保留的恢复路径。
- 本项目是 AI 辅助服务器管理的操作指导，不能替代你对实际命令的理解。

## 校验

发布修改前运行仓库校验：

```bash
python scripts/validate_skill.py
```

校验脚本会检查必要文件、frontmatter，以及常见的密钥和个人信息模式。

## 支持目标

这个 skill 面向使用 OpenSSH、systemd、UFW 和 fail2ban 的 Ubuntu/Debian 系统。其他发行版、防火墙系统、init 系统和 SSH 实现需要谨慎适配。

## 友链

- [LINUX DO](https://linux.do)

## 许可证

MIT 许可证。见 [LICENSE](LICENSE)。
