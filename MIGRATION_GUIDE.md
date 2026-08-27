# Migration Guide - Moving DQ Agent to Different Accounts

## 📋 Overview

This guide covers how to move the Data Quality Agent to:
1. Different GitHub Account
2. Different GitHub Copilot Account
3. Different AWS Account

---

## 🔄 Scenario 1: Move to Different GitHub Account

If you want to move the repository to a different GitHub account:

### Method A: Fork the Repository (Recommended)

```bash
# 1. On GitHub.com, navigate to:
https://github.com/karthikkatca/mysvcagt

# 2. Click "Fork" button (top right)
# 3. Select your new account
# 4. The entire repository is copied to new account

# 5. Clone to your local machine
git clone https://github.com/YOUR-NEW-ACCOUNT/mysvcagt.git
cd mysvcagt
```

### Method B: Create New Repository and Push

```bash
# 1. On new GitHub account, create empty repository named "mysvcagt"

# 2. On local machine, update remote URL
cd E:\mygit\mysvcagt
git remote set-url origin https://github.com/NEW-ACCOUNT/mysvcagt.git

# 3. Push to new account
git push -u origin main

# 4. Verify
git remote -v
```

### Method C: Download and Re-upload

```bash
# 1. Download ZIP from current repo
# https://github.com/karthikkatca/mysvcagt/archive/refs/heads/main.zip

# 2. Extract to new location
# E:\mygit\mysvcagt-new\

# 3. Initialize new Git repo
cd E:\mygit\mysvcagt-new
git init
git branch -m main

# 4. Add remote (new account)
git remote add origin https://github.com/NEW-ACCOUNT/mysvcagt.git

# 5. Commit and push
git add .
git commit -m "Initial commit from migration"
git push -u origin main
```

### What Gets Transferred
✅ All code files
✅ Configuration files (CSV)
✅ Documentation (all .md files)
✅ Git history (if using fork or push method)
✅ Folder structure
✅ .gitignore settings

### What Needs Updating
- GitHub repository URL in documentation (optional)
- Git remote URL (if using local clone)

---

## 💻 Scenario 2: Move to Different GitHub Copilot Account

If you want to work on this project from a different Copilot account/workspace:

### Option A: Clone from GitHub (Recommended)

```bash
# 1. In new Copilot workspace/account
git clone https://github.com/karthikkatca/mysvcagt.git
cd mysvcagt

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test the agent
cd scripts
python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne

# That's it! Ready to use.
```

### Option B: Share Files Directly

```bash
# 1. From original location, copy entire folder
# Copy: E:\mygit\mysvcagt
# To: New machine location (e.g., C:\Users\NewUser\projects\mysvcagt)

# 2. In new Copilot account, open the folder
cd C:\Users\NewUser\projects\mysvcagt

# 3. Reconnect Git remote (if needed)
git remote -v
# If not connected:
git remote add origin https://github.com/karthikkatca/mysvcagt.git

# 4. Install dependencies
pip install -r requirements.txt

# 5. Test
cd scripts
python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne
```

### What's Needed
✅ Entire project folder (all files)
✅ Python 3.8+ installed
✅ Install requirements: `pip install -r requirements.txt`
✅ Git configured (if you want to push changes)

### What's NOT Needed
❌ Just the README file (not sufficient)
❌ Re-creating files manually
❌ Reconfiguring the agent logic

---

## ☁️ Scenario 3: Move to Different AWS Account

If deploying to a different AWS account:

### Prerequisites Checklist
- [ ] New AWS account with appropriate permissions
- [ ] AWS CLI configured with new account credentials
- [ ] Python code files from GitHub repo
- [ ] Configuration CSV files

### Step 1: Get the Code

```bash
# Clone repository
git clone https://github.com/karthikkatca/mysvcagt.git
cd mysvcagt
```

### Step 2: Update AWS-Specific Configuration

**Files that need AWS account-specific updates:**

1. **S3 Bucket Names** (in your deployment)
   ```bash
   # Change from:
   s3://your-company-dq-pipeline/
   
   # To:
   s3://new-company-dq-pipeline/
   ```

2. **Redshift Connection** (in Glue job parameters)
   - Update host: `new-redshift-cluster.xxx.redshift.amazonaws.com`
   - Update database name, user, password
   - Store in AWS Secrets Manager

3. **IAM Roles** (all ARNs need updating)
   ```bash
   # Old: arn:aws:iam::OLD-ACCOUNT-ID:role/GlueServiceRole
   # New: arn:aws:iam::NEW-ACCOUNT-ID:role/GlueServiceRole
   ```

4. **Lambda Function** (new deployment)
   - Update MWAA environment name
   - Update S3 bucket references
   - Update IAM execution role

### Step 3: Deploy to New AWS Account

```bash
# 1. Configure AWS CLI for new account
aws configure
# Enter: Access Key ID, Secret Key, Region

# 2. Create S3 bucket in new account
BUCKET="new-company-dq-pipeline"
aws s3 mb s3://$BUCKET

# 3. Create folder structure
aws s3api put-object --bucket $BUCKET --key inbound/
aws s3api put-object --bucket $BUCKET --key clean/
aws s3api put-object --bucket $BUCKET --key quarantine/
aws s3api put-object --bucket $BUCKET --key scripts/

# 4. Upload scripts
aws s3 cp scripts/glue_job_wrapper.py s3://$BUCKET/scripts/
aws s3 cp scripts/schema_evolution_agent.py s3://$BUCKET/scripts/

# 5. Create Redshift cluster in new account
# (Follow AWS_Deployment_Guide.md)

# 6. Create database tables
# (Run SQL from AWS_Deployment_Guide.md)

# 7. Load configuration data
aws s3 cp control/config/framework_inbound_config.csv s3://$BUCKET/temp/
aws s3 cp control/rules/dq_rule_catalog.csv s3://$BUCKET/temp/

# Then COPY to Redshift (update ARN for new account):
# COPY framework_inbound_config FROM 's3://...'
# IAM_ROLE 'arn:aws:iam::NEW-ACCOUNT-ID:role/RedshiftCopyRole'

# 8. Create Glue job with new IAM role
aws glue create-job \
  --name dq-agent-job \
  --role arn:aws:iam::NEW-ACCOUNT-ID:role/GlueServiceRole \
  --command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/glue_job_wrapper.py

# 9. Create Lambda function (new ARN)
# 10. Setup MWAA (new environment)
```

### Configuration Files to Update

**framework_inbound_config.csv**
```csv
# Update S3 paths for new account
s3_inbound_path,s3://NEW-BUCKET/inbound/sourceone/
s3_quarantine_path,s3://NEW-BUCKET/quarantine/sourceone/
s3_clean_path,s3://NEW-BUCKET/clean/sourceone/
```

### What Gets Transferred
✅ Python code (no changes needed)
✅ Configuration logic (no changes needed)
✅ DQ rules structure (data may need review)
✅ Documentation (reference)

### What Needs New Setup
❌ S3 buckets (new account)
❌ Redshift cluster (new account)
❌ IAM roles & policies (new ARNs)
❌ Glue jobs (new job definitions)
❌ Lambda functions (new deployments)
❌ MWAA environment (if used)
❌ Secrets Manager entries

---

## 📝 Quick Migration Checklist

### For GitHub Account Change
- [ ] Fork repo OR push to new remote
- [ ] Clone to local machine
- [ ] Update Git remote URL
- [ ] Install dependencies
- [ ] Test locally

### For Copilot Account Change
- [ ] Clone from GitHub
- [ ] Install Python dependencies
- [ ] Test agent locally
- [ ] Configure Git (if making changes)

### For AWS Account Change
- [ ] Clone code from GitHub
- [ ] Create S3 buckets (new names)
- [ ] Create Redshift cluster
- [ ] Create database tables
- [ ] Load configuration data
- [ ] Create IAM roles (new ARNs)
- [ ] Deploy Glue jobs
- [ ] Deploy Lambda functions
- [ ] Setup MWAA/Airflow
- [ ] Update all resource references
- [ ] Test end-to-end

---

## ⚠️ Common Mistakes to Avoid

### ❌ DON'T: Copy only README
**Why**: README is documentation. You need actual code files.

### ❌ DON'T: Forget dependencies
**Why**: Agent needs Python packages (pandas, etc.)

### ❌ DON'T: Reuse old AWS resource ARNs
**Why**: ARNs are account-specific. Must create new ones.

### ❌ DON'T: Skip testing
**Why**: Always test locally before AWS deployment.

### ✅ DO: Clone entire repository
**Why**: Gets all files with correct structure.

### ✅ DO: Follow AWS_Deployment_Guide.md
**Why**: Step-by-step instructions for new AWS setup.

### ✅ DO: Update S3 bucket names
**Why**: S3 bucket names are globally unique.

### ✅ DO: Test incrementally
**Why**: Easier to debug one component at a time.

---

## 🎯 Recommended Migration Path

### Simplest: New Copilot Account (Same GitHub)
```bash
# Just clone and run
git clone https://github.com/karthikkatca/mysvcagt.git
cd mysvcagt
pip install -r requirements.txt
cd scripts
python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne
# Done!
```

### Medium: New GitHub Account
```bash
# Fork on GitHub.com, then clone
git clone https://github.com/NEW-ACCOUNT/mysvcagt.git
cd mysvcagt
pip install -r requirements.txt
# Ready to use
```

### Complex: New AWS Account
```bash
# Clone code, then follow full AWS setup
git clone https://github.com/karthikkatca/mysvcagt.git
cd mysvcagt

# Then follow AWS_Deployment_Guide.md completely
# - Create all AWS resources from scratch
# - Update all account-specific configurations
# - Deploy and test each component
# Allow 4-6 weeks for complete setup
```

---

## 📞 Need Help?

**Documentation Available**:
- README.md - Local setup and usage
- AWS_Deployment_Guide.md - Complete AWS setup
- AWS_S3_UPLOAD_MAPPING.md - File upload guide
- VSCODE_SETUP_GUIDE.md - Development workflow
- CHAT_HISTORY_SUMMARY.md - Complete session history

**GitHub Repository**:
https://github.com/karthikkatca/mysvcagt

---

## 🔑 Key Points Summary

1. **README alone is NOT enough** - you need all the code files
2. **Easiest migration**: Clone from GitHub (gets everything)
3. **GitHub account change**: Fork or push to new remote
4. **Copilot account change**: Just clone and install dependencies
5. **AWS account change**: Complete new infrastructure setup required
6. **Always test locally first** before AWS deployment
7. **Use AWS_Deployment_Guide.md** for step-by-step AWS setup

---

**Migration Status**: Document created  
**Ready to Use**: Follow appropriate section above based on your migration scenario
