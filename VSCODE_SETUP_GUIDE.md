# VS Code Setup Guide for mysvcagt Repository

## ✅ Current Git Configuration

Your local folder is **already configured** and connected to GitHub:

```
Local Folder:  E:\mygit\mysvcagt
Remote URL:    https://github.com/karthikkatca/mysvcagt.git
Branch:        main (tracking origin/main)
Status:        ✅ Up to date, all changes pushed
```

---

## 🚀 How to Open in Visual Studio Code

### Method 1: Open from File Explorer (Easiest)

1. Right-click on the folder `E:\mygit\mysvcagt`
2. Select **"Open with Code"** (if available)
   - OR select **"Open in Terminal"** → then type: `code .`

### Method 2: Open from VS Code

1. Open Visual Studio Code
2. Click **File → Open Folder**
3. Navigate to: `E:\mygit\mysvcagt`
4. Click **"Select Folder"**

### Method 3: Command Line

```bash
# Open VS Code directly
cd E:\mygit\mysvcagt
code .
```

---

## 📝 Making Changes and Pushing to Remote

Once opened in VS Code, you can make changes and push them to GitHub:

### Step 1: Make Your Changes
- Edit any file in VS Code
- Save your changes (Ctrl+S)

### Step 2: Stage Changes (3 ways to do this)

**Option A: Using VS Code Source Control Panel**
1. Click the **Source Control** icon in the left sidebar (or Ctrl+Shift+G)
2. You'll see all changed files
3. Click the **"+"** icon next to each file to stage them
   - Or click **"+"** next to "Changes" to stage all files

**Option B: Using VS Code Terminal**
1. Open terminal in VS Code: **View → Terminal** (or Ctrl+`)
2. Run commands:
```bash
git add .                    # Stage all changes
git add filename.py          # Stage specific file
```

**Option C: Using Command Palette**
1. Press **Ctrl+Shift+P**
2. Type **"Git: Stage"** and select the option

### Step 3: Commit Changes

**Option A: Using VS Code Source Control Panel**
1. In Source Control panel, type your commit message in the text box
2. Click the **✓ Commit** button (or Ctrl+Enter)

**Option B: Using Terminal**
```bash
git commit -m "Your commit message here"
```

### Step 4: Push to Remote

**Option A: Using VS Code**
1. In Source Control panel, click the **"..."** menu
2. Select **"Push"**
   - Or use the sync button (↻ icon) at the bottom status bar

**Option B: Using Terminal**
```bash
git push origin main
```

---

## 📊 VS Code Git Status Indicators

When you open the folder in VS Code, you'll see:

- **Source Control badge**: Shows number of changed files
- **File colors in Explorer**:
  - 🟢 Green: New/untracked files
  - 🟡 Yellow/Orange: Modified files
  - 🔴 Red: Deleted files
  - ⚪ White: Unchanged files
- **Bottom status bar**:
  - Branch name: "main"
  - Sync arrows: Shows commits ahead/behind remote

---

## 🔄 Full Workflow Example

```bash
# 1. Open folder in VS Code
cd E:\mygit\mysvcagt
code .

# 2. Make changes to files in VS Code editor
# (e.g., edit scripts/dq_agent_local.py)

# 3. In VS Code terminal (Ctrl+`):
git status                               # See what changed
git add .                                # Stage all changes
git commit -m "Update DQ agent logic"    # Commit changes
git push origin main                     # Push to GitHub

# 4. Verify on GitHub
# Visit: https://github.com/karthikkatca/mysvcagt
```

---

## 🌿 Working with Branches

If you want to create a new branch for features:

### Using VS Code

1. Click on **"main"** in the bottom-left status bar
2. Select **"Create new branch..."**
3. Enter branch name (e.g., `feature/new-rule-type`)
4. VS Code automatically switches to the new branch

### Using Terminal

```bash
# Create and switch to new branch
git checkout -b feature/new-rule-type

# Make your changes, then commit
git add .
git commit -m "Add new rule type"

# Push new branch to remote
git push -u origin feature/new-rule-type

# Switch back to main
git checkout main

# Merge feature branch (after testing)
git merge feature/new-rule-type
git push origin main
```

---

## 🔍 Useful VS Code Git Features

### 1. View File History
- Right-click any file → **"Open Timeline"**
- Shows all commits that changed the file

### 2. Compare Changes
- Click on a changed file in Source Control panel
- VS Code shows side-by-side diff

### 3. Undo Changes
- In Source Control, click **"↩"** (discard) next to a file
- Reverts unsaved changes

### 4. Pull Latest Changes
```bash
git pull origin main
```
Or use VS Code: Source Control → **"..."** → **"Pull"**

### 5. View Commit History
- Install extension: **"Git Graph"** or **"GitLens"**
- View visual commit history

---

## 🛠️ Recommended VS Code Extensions

Install these for better Git/Python experience:

```
1. GitLens — Git supercharged
2. Git Graph — Visual commit history
3. Python — Official Python support
4. Pylance — Python language server
5. autoDocstring — Python docstring generator
6. Better Comments — Enhanced comment highlighting
```

**Install via**:
- Ctrl+Shift+X → Search extension name → Click Install

---

## ⚠️ Important Notes

### Git Configuration (Already Set)
Your repository is configured with:
```bash
User name:  DQ Agent User
User email: user@example.com
```

To update if needed:
```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### Authentication
When pushing to GitHub, you may be asked for credentials:
- **Recommended**: Use GitHub Personal Access Token (PAT)
- **Alternative**: Use GitHub CLI (`gh auth login`)

To set up PAT:
1. GitHub.com → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Give it `repo` scope
4. Use token as password when pushing

### .gitignore
Already configured to ignore:
- `logs/` - Local log files
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python files
- `.vscode/` - VS Code settings (optional)

---

## 🎯 Quick Reference Commands

```bash
# Check status
git status

# Stage changes
git add .                    # All files
git add filename.py          # Specific file

# Commit
git commit -m "message"

# Push to remote
git push origin main

# Pull from remote
git pull origin main

# View remote info
git remote -v

# View branch info
git branch -vv

# Create new branch
git checkout -b branch-name

# Switch branch
git checkout main

# View commit history
git log --oneline -10
```

---

## ✅ Quick Start Checklist

- [x] Local folder is a Git repository
- [x] Remote is connected to GitHub
- [x] Main branch tracks origin/main
- [x] All files are committed and pushed
- [ ] Open folder in VS Code: `code E:\mygit\mysvcagt`
- [ ] Install recommended extensions
- [ ] Make a test change and push it!

---

## 📚 Additional Resources

- **VS Code Git Tutorial**: https://code.visualstudio.com/docs/sourcecontrol/overview
- **Git Basics**: https://git-scm.com/book/en/v2/Getting-Started-Git-Basics
- **GitHub Docs**: https://docs.github.com/en/get-started

---

**Your Repository**: https://github.com/karthikkatca/mysvcagt  
**Local Path**: E:\mygit\mysvcagt  
**Status**: ✅ Ready to use in VS Code!
