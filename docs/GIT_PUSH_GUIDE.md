# GitHub Push 手动执行指南

## 在你的 Windows 电脑上执行

### 步骤 1：打开 Git Bash 或 PowerShell

在 salmon-pms 项目文件夹上右键 → **Git Bash Here**

### 步骤 2：检查当前状态

```bash
cd salmon-pms
git status
```

应该看到：
```
On branch main
Your branch is ahead of 'origin/main' by 2 commits.
```

### 步骤 3：直接 Push

```bash
git push origin main
```

### 如果提示输入密码

因为远程仓库 URL 是 HTTPS，可能会提示输入 GitHub 密码。请输入你的 **GitHub Personal Access Token**（不是登录密码）：

```
注意：Token是敏感信息，不要写在文件里
```

### 如果 push 被拒绝（冲突）

```bash
# 先拉取远程最新代码
git pull origin main

# 如果有冲突，解决后提交
git add .
git commit -m "merge remote changes"

# 再 push
git push origin main
```

### 验证 Push 成功

```bash
git log --oneline -3
```

应该显示：
```
69f8042 feat: PostgreSQL migration + notification system + invoice fixes
ae5258f fix: invoice net weight display + round-up decimal fix
0605bd2 fix: integration fixes for outsourced finished-product-sales module
```

然后访问 https://github.com/snsusannah-byte/salmon-pms 查看最新 commit。

---

## 常见问题

**Q: 提示 "fatal: unable to access"**
A: 检查网络连接，或尝试：
```bash
git remote set-url origin https://github.com/snsusannah-byte/salmon-pms.git
git push origin main
```
然后输入你的 GitHub 用户名和密码（Token）。

**Q: 提示 "rejected: non-fast-forward"**
A: 先执行 `git pull origin main` 合并远程变更，再 push。

**Q: 不想每次输入密码**
A: 配置 Git Credential Manager：
```bash
git config --global credential.helper manager
```
第一次输入后，Windows 会记住密码。
