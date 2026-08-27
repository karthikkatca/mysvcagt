# AWS S3 Upload Mapping Guide

## Files to Upload to AWS S3

### 📋 Complete Mapping Table

| # | Local Path (E:\mygit\mysvcagt\) | S3 Destination | Purpose | Required |
|---|--------------------------------|----------------|---------|----------|
| **CONFIGURATION FILES** |
| 1 | `control/config/framework_inbound_config.csv` | Load to **Redshift Table** | Source configuration metadata | ✅ Critical |
| 2 | `control/rules/dq_rule_catalog.csv` | Load to **Redshift Table** | Data quality rules catalog | ✅ Critical |
| **AWS GLUE SCRIPTS** |
| 3 | `scripts/glue_job_wrapper.py` | `s3://YOUR-BUCKET/scripts/glue_job_wrapper.py` | Main Glue job entry point | ✅ Critical |
| 4 | `scripts/schema_evolution_agent.py` | `s3://YOUR-BUCKET/scripts/schema_evolution_agent.py` | Core DQ agent logic | ✅ Critical |
| 5 | `scripts/glue_dependencies.zip` | `s3://YOUR-BUCKET/scripts/glue_dependencies.zip` | Python dependencies (optional) | ⚪ Optional |
| **LAMBDA FUNCTION** |
| 6 | Create new: `lambda_s3_trigger.py` | AWS Lambda Console | S3 event trigger handler | ✅ Critical |
| **AIRFLOW DAG** |
| 7 | Create new: `dq_agent_pipeline.py` | `s3://YOUR-BUCKET/dags/dq_agent_pipeline.py` | MWAA workflow orchestration | ✅ Critical |
| **CHATBOT/API (OPTIONAL)** |
| 8 | `scripts/dataops_chatbot.py` | `s3://YOUR-BUCKET/api/dataops_chatbot.py` | LLM query interface | ⚪ Optional |
| **TEST DATA** |
| 9 | `inbound/SourceOne_mbr_20260826.txt` | `s3://YOUR-BUCKET/inbound/sourceone/SourceOne_mbr_20260826.txt` | Sample test file | 🧪 Testing |
| **DOCUMENTATION (REFERENCE ONLY)** |
| 10 | `README.md` | Not uploaded (reference only) | Local execution guide | 📖 Reference |
| 11 | `AWS_Deployment_Guide.md` | Not uploaded (reference only) | AWS deployment instructions | 📖 Reference |
| 12 | `PROJECT_SUMMARY.md` | Not uploaded (reference only) | Project overview | 📖 Reference |
| 13 | `AWS_GUIDE_README.md` | Not uploaded (reference only) | Guide viewing instructions | 📖 Reference |
| **LOCAL DEVELOPMENT ONLY** |
| 14 | `scripts/dq_agent_local.py` | Not uploaded (local testing only) | CSV-based local agent | 💻 Local Only |
| 15 | `scripts/convert_md_to_pdf.py` | Not uploaded | PDF conversion utility | 💻 Local Only |
| 16 | `scripts/md_to_pdf_simple.py` | Not uploaded | PDF conversion utility | 💻 Local Only |
| 17 | `scripts/agent_config.py` | Review first | Configuration helper | ⚠️ Review |
| 18 | `requirements.txt` | Not uploaded (for local dev) | Python dependencies | 💻 Local Only |

---

## 🎯 Critical Files for AWS Deployment

### Priority 1: Configuration Data (Load to Redshift)

```bash
# These CSV files contain metadata - load them into Redshift tables

# 1. Load framework_inbound_config.csv to Redshift
Local:  control/config/framework_inbound_config.csv
Target: Redshift table: framework_inbound_config
Method: COPY command or SQL INSERT

# 2. Load dq_rule_catalog.csv to Redshift  
Local:  control/rules/dq_rule_catalog.csv
Target: Redshift table: dq_rule_catalog
Method: COPY command or SQL INSERT
```

### Priority 2: AWS Glue Scripts

```bash
# Upload Python scripts to S3 for Glue job

aws s3 cp E:\mygit\mysvcagt\scripts\glue_job_wrapper.py \
  s3://your-company-dq-pipeline/scripts/glue_job_wrapper.py

aws s3 cp E:\mygit\mysvcagt\scripts\schema_evolution_agent.py \
  s3://your-company-dq-pipeline/scripts/schema_evolution_agent.py

# Optional: Additional Python modules
aws s3 cp E:\mygit\mysvcagt\scripts\glue_dependencies.zip \
  s3://your-company-dq-pipeline/scripts/glue_dependencies.zip
```

### Priority 3: Lambda Function

```bash
# Lambda function needs to be created separately
# Use code from AWS_Deployment_Guide.md section 6
# The lambda_s3_trigger.py code is in the guide (not in repo)

File: lambda_s3_trigger.py (create from guide)
Target: AWS Lambda function: dq-agent-s3-trigger
```

### Priority 4: Airflow DAG

```bash
# Create DAG file from AWS_Deployment_Guide.md section 7
# The dq_agent_pipeline.py code is in the guide (not in repo)

aws s3 cp dq_agent_pipeline.py \
  s3://your-company-dq-pipeline/dags/dq_agent_pipeline.py
```

### Priority 5: Test Data

```bash
# Upload sample file for testing

aws s3 cp E:\mygit\mysvcagt\inbound\SourceOne_mbr_20260826.txt \
  s3://your-company-dq-pipeline/inbound/sourceone/SourceOne_mbr_20260826.txt
```

---

## 📊 Detailed S3 Bucket Structure

```
s3://your-company-dq-pipeline/
│
├── inbound/                          # Landing zone for incoming files
│   ├── sourceone/
│   │   └── SourceOne_mbr_*.txt      # From: inbound/SourceOne_mbr_20260826.txt
│   └── sourcetwo/
│       └── SourceTwo_*.csv
│
├── clean/                            # Processed clean data (output)
│   ├── sourceone/
│   └── sourcetwo/
│
├── quarantine/                       # Quarantined bad data (output)
│   ├── sourceone/
│   └── sourcetwo/
│
├── scripts/                          # Glue job scripts
│   ├── glue_job_wrapper.py          # From: scripts/glue_job_wrapper.py ✅
│   ├── schema_evolution_agent.py    # From: scripts/schema_evolution_agent.py ✅
│   └── glue_dependencies.zip        # From: scripts/glue_dependencies.zip (optional)
│
├── dags/                             # Airflow DAGs (for MWAA)
│   └── dq_agent_pipeline.py         # Create from deployment guide ✅
│
├── api/                              # Optional: API/Chatbot
│   └── dataops_chatbot.py           # From: scripts/dataops_chatbot.py (optional)
│
└── temp/                             # Glue job temporary files
```

---

## 🚀 Step-by-Step Upload Commands

### Step 1: Create S3 Bucket Structure

```bash
# Set your bucket name
BUCKET_NAME="your-company-dq-pipeline"

# Create bucket (if not exists)
aws s3 mb s3://$BUCKET_NAME

# Create folder structure
aws s3api put-object --bucket $BUCKET_NAME --key inbound/
aws s3api put-object --bucket $BUCKET_NAME --key clean/
aws s3api put-object --bucket $BUCKET_NAME --key quarantine/
aws s3api put-object --bucket $BUCKET_NAME --key scripts/
aws s3api put-object --bucket $BUCKET_NAME --key dags/
aws s3api put-object --bucket $BUCKET_NAME --key temp/
```

### Step 2: Upload Glue Scripts

```bash
# Navigate to project folder
cd E:\mygit\mysvcagt

# Upload main Glue job script
aws s3 cp scripts\glue_job_wrapper.py s3://$BUCKET_NAME/scripts/glue_job_wrapper.py

# Upload core agent script
aws s3 cp scripts\schema_evolution_agent.py s3://$BUCKET_NAME/scripts/schema_evolution_agent.py

# Optional: Upload dependencies
aws s3 cp scripts\glue_dependencies.zip s3://$BUCKET_NAME/scripts/glue_dependencies.zip

# Verify upload
aws s3 ls s3://$BUCKET_NAME/scripts/
```

### Step 3: Upload Chatbot (Optional)

```bash
# Upload chatbot API
aws s3 cp scripts\dataops_chatbot.py s3://$BUCKET_NAME/api/dataops_chatbot.py
```

### Step 4: Upload Test Data

```bash
# Upload sample test file
aws s3 cp inbound\SourceOne_mbr_20260826.txt s3://$BUCKET_NAME/inbound/sourceone/SourceOne_mbr_20260826.txt

# Verify upload
aws s3 ls s3://$BUCKET_NAME/inbound/sourceone/
```

### Step 5: Load Configuration to Redshift

```sql
-- Connect to Redshift using psql or SQL client

-- 1. Upload CSV to S3 first
aws s3 cp control\config\framework_inbound_config.csv s3://$BUCKET_NAME/temp/framework_inbound_config.csv
aws s3 cp control\rules\dq_rule_catalog.csv s3://$BUCKET_NAME/temp/dq_rule_catalog.csv

-- 2. Then COPY to Redshift tables

-- Load framework config
COPY framework_inbound_config
FROM 's3://your-company-dq-pipeline/temp/framework_inbound_config.csv'
IAM_ROLE 'arn:aws:iam::YOUR-ACCOUNT:role/RedshiftCopyRole'
CSV
IGNOREHEADER 1;

-- Load DQ rules
COPY dq_rule_catalog
FROM 's3://your-company-dq-pipeline/temp/dq_rule_catalog.csv'
IAM_ROLE 'arn:aws:iam::YOUR-ACCOUNT:role/RedshiftCopyRole'
CSV
IGNOREHEADER 1;

-- Verify loaded data
SELECT COUNT(*) FROM framework_inbound_config;
SELECT COUNT(*) FROM dq_rule_catalog;
```

---

## ⚠️ Files NOT to Upload

| File | Reason |
|------|--------|
| `scripts/dq_agent_local.py` | Local testing only - uses CSV files instead of Redshift |
| `requirements.txt` | For local Python environment, not needed in AWS |
| `README.md` | Documentation - keep in GitHub repo only |
| `AWS_Deployment_Guide.md` | Documentation - reference guide |
| `PROJECT_SUMMARY.md` | Documentation - project summary |
| `.gitignore` | Git configuration file |
| `logs/*` | Local log files - not for AWS |
| `clean/*` | Local output folder - not for AWS |
| `quarantine/*` | Local output folder - not for AWS |
| PDF conversion scripts | Local utilities only |

---

## 🔍 Verification Checklist

After uploading, verify each component:

### S3 Verification
```bash
# Check all uploaded files
aws s3 ls s3://$BUCKET_NAME/scripts/ --recursive
aws s3 ls s3://$BUCKET_NAME/inbound/ --recursive
aws s3 ls s3://$BUCKET_NAME/dags/ --recursive
```

### Redshift Verification
```sql
-- Verify configuration loaded
SELECT source_name, file_pattern, enable_deduplication 
FROM framework_inbound_config;

-- Verify rules loaded
SELECT rule_name, source_name, enabled 
FROM dq_rule_catalog 
WHERE enabled = TRUE;
```

### Glue Job Verification
```bash
# Check if Glue job can access scripts
aws glue get-job --job-name dq-agent-job
```

---

## 📝 Summary

**Total Files to Upload:** 5-7 files
- ✅ 2 Configuration CSV files (load to Redshift)
- ✅ 2 Glue Python scripts (to S3)
- ✅ 1 Test data file (to S3)
- ⚪ 1 Chatbot script (optional)
- ✅ 1 Airflow DAG (create from guide, upload to S3)

**Files to Create from Guide:** 2 files
- Lambda function: `lambda_s3_trigger.py`
- Airflow DAG: `dq_agent_pipeline.py`

**Documentation:** Available in GitHub repo for reference
- https://github.com/karthikkatca/mysvcagt

---

**Next Step:** Follow the detailed instructions in `AWS_Deployment_Guide.md` for complete AWS setup!
