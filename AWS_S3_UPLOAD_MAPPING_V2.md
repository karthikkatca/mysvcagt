# AWS S3 Upload Mapping - S3 File-Based Version
## Updated for S3 Configuration Files (NO REDSHIFT DEPENDENCY)

**Last Updated**: 2026-08-27  
**Version**: 2.0 (S3 File-Based)

---

## Overview

This document maps local files to AWS S3 destinations for the **S3 file-based** DQ Agent implementation. 

**Key Change from v1.0:**
- ❌ **NO Redshift tables** - Configuration files are stored directly in S3 as CSV files
- ✅ **All configuration in S3** - Config CSVs uploaded to S3 control folder
- ✅ **Simplified architecture** - No database connections, all file-based
- ✅ **Lower cost** - No Redshift cluster costs

---

## S3 Bucket Structure

```
s3://your-company-dq-pipeline/
├── inbound/                    # Landing zone for incoming files
│   └── SourceOne_mbr_YYYYMMDD.txt
├── clean/                      # Clean records after DQ processing
│   └── SourceOne_mbr_YYYYMMDD_clean_timestamp.csv
├── quarantine/                 # Quarantined records
│   ├── SourceOne_mbr_YYYYMMDD_QUARANTINED_timestamp.csv
│   ├── SourceOne_mbr_YYYYMMDD_duplicates_timestamp.csv
│   └── SourceOne_mbr_YYYYMMDD_bad_records_timestamp.csv
├── logs/                       # Anomaly logs and quarantine manifests
│   ├── anomaly_log_runid_timestamp.csv
│   └── quarantine_manifest_runid_timestamp.csv
├── control/                    # Configuration files (CSV)
│   ├── config/
│   │   └── framework_inbound_config.csv
│   └── rules/
│       └── dq_rule_catalog.csv
├── scripts/                    # Glue job Python scripts
│   ├── glue_job_wrapper_s3.py
│   ├── schema_evolution_agent_s3.py
│   └── agent_config.py
└── temp/                       # Temporary processing files
```

---

## File Upload Mapping Table

| Priority | Local File | S3 Destination | Upload Action | Notes |
|----------|------------|----------------|---------------|-------|
| **1** | `control/config/framework_inbound_config.csv` | `s3://bucket/control/config/framework_inbound_config.csv` | Upload to S3 | **CRITICAL** - Source configuration CSV |
| **1** | `control/rules/dq_rule_catalog.csv` | `s3://bucket/control/rules/dq_rule_catalog.csv` | Upload to S3 | **CRITICAL** - DQ rules CSV |
| **2** | `scripts/glue_job_wrapper_s3.py` | `s3://bucket/scripts/glue_job_wrapper_s3.py` | Upload to S3 | **CRITICAL** - Glue job entry point (S3 version) |
| **2** | `scripts/schema_evolution_agent_s3.py` | `s3://bucket/scripts/schema_evolution_agent_s3.py` | Upload to S3 | **CRITICAL** - Core agent logic (S3 version) |
| **3** | `scripts/agent_config.py` | `s3://bucket/scripts/agent_config.py` | Upload to S3 | Agent configuration module |
| **4** | `scripts/glue_dependencies.zip` | `s3://bucket/scripts/glue_dependencies.zip` | Upload to S3 | Python dependencies (if needed) |
| **5** | `inbound/SourceOne_mbr_20260826.txt` | `s3://bucket/inbound/SourceOne_mbr_20260826.txt` | Upload to S3 | **TESTING** - Sample test file |
| **6** | `README.md` | Keep local / GitHub | No upload | Documentation |
| **6** | `AWS_Deployment_Guide_S3.md` | Keep local / GitHub | No upload | Deployment instructions |
| **6** | `requirements.txt` | Keep local / GitHub | No upload | Local dev dependencies |
| **6** | `.gitignore` | Keep local / GitHub | No upload | Git configuration |

---

## Detailed Upload Instructions

### Step 1: Create S3 Bucket

```bash
# Set your bucket name
BUCKET_NAME="your-company-dq-pipeline"
AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://${BUCKET_NAME} --region ${AWS_REGION}

# Create folder structure
aws s3api put-object --bucket ${BUCKET_NAME} --key inbound/
aws s3api put-object --bucket ${BUCKET_NAME} --key clean/
aws s3api put-object --bucket ${BUCKET_NAME} --key quarantine/
aws s3api put-object --bucket ${BUCKET_NAME} --key logs/
aws s3api put-object --bucket ${BUCKET_NAME} --key control/config/
aws s3api put-object --bucket ${BUCKET_NAME} --key control/rules/
aws s3api put-object --bucket ${BUCKET_NAME} --key scripts/
aws s3api put-object --bucket ${BUCKET_NAME} --key temp/
```

### Step 2: Upload Configuration Files (Priority 1)

```bash
# Navigate to local repo
cd E:\mygit\mysvcagt

# Upload source configuration CSV
aws s3 cp control/config/framework_inbound_config.csv \
    s3://${BUCKET_NAME}/control/config/framework_inbound_config.csv

# Upload DQ rules CSV
aws s3 cp control/rules/dq_rule_catalog.csv \
    s3://${BUCKET_NAME}/control/rules/dq_rule_catalog.csv

# Verify uploads
aws s3 ls s3://${BUCKET_NAME}/control/config/
aws s3 ls s3://${BUCKET_NAME}/control/rules/
```

### Step 3: Upload S3-Based Glue Scripts (Priority 2)

```bash
# Upload S3-based Glue job wrapper
aws s3 cp scripts/glue_job_wrapper_s3.py \
    s3://${BUCKET_NAME}/scripts/glue_job_wrapper_s3.py

# Upload S3-based schema evolution agent
aws s3 cp scripts/schema_evolution_agent_s3.py \
    s3://${BUCKET_NAME}/scripts/schema_evolution_agent_s3.py

# Verify uploads
aws s3 ls s3://${BUCKET_NAME}/scripts/
```

### Step 4: Upload Supporting Scripts (Priority 3-4)

```bash
# Upload agent config
aws s3 cp scripts/agent_config.py \
    s3://${BUCKET_NAME}/scripts/agent_config.py

# Upload dependencies if needed
aws s3 cp scripts/glue_dependencies.zip \
    s3://${BUCKET_NAME}/scripts/glue_dependencies.zip
```

### Step 5: Upload Test Data (Priority 5)

```bash
# Upload sample test file
aws s3 cp inbound/SourceOne_mbr_20260826.txt \
    s3://${BUCKET_NAME}/inbound/SourceOne_mbr_20260826.txt

# Verify upload
aws s3 ls s3://${BUCKET_NAME}/inbound/
```

---

## Files NOT Uploaded (Local/GitHub Only)

| File | Location | Reason |
|------|----------|--------|
| `README.md` | GitHub | Documentation only |
| `AWS_Deployment_Guide_S3.md` | GitHub | Instructions |
| `AWS_S3_UPLOAD_MAPPING_V2.md` | GitHub | This mapping document |
| `MIGRATION_GUIDE.md` | GitHub | Migration instructions |
| `VSCODE_SETUP_GUIDE.md` | GitHub | Development guide |
| `requirements.txt` | GitHub | Local dev dependencies |
| `.gitignore` | GitHub | Git configuration |
| `scripts/dq_agent_local.py` | Local/GitHub | **Local execution only** |
| `logs/*.log` | Local | Generated locally, excluded from Git |
| `clean/*.txt` | Local | Output files (generated) |
| `quarantine/*.csv` | Local | Output files (generated) |

---

## Old Redshift-Based Scripts (NOT USED)

These files are kept in the repository for reference but are **NOT uploaded to S3** in the S3 file-based implementation:

| File | Status | Notes |
|------|--------|-------|
| `scripts/glue_job_wrapper.py` | Deprecated | Old Redshift version |
| `scripts/schema_evolution_agent.py` | Deprecated | Old Redshift version |
| `scripts/dataops_chatbot.py` | Optional | LLM chatbot (requires Redshift) |

**Action**: Use the new S3 versions:
- `glue_job_wrapper_s3.py` (replaces glue_job_wrapper.py)
- `schema_evolution_agent_s3.py` (replaces schema_evolution_agent.py)

---

## Verification Steps

### Verify Configuration Files

```bash
# Download and inspect uploaded CSVs
aws s3 cp s3://${BUCKET_NAME}/control/config/framework_inbound_config.csv - | head -5
aws s3 cp s3://${BUCKET_NAME}/control/rules/dq_rule_catalog.csv - | head -5
```

### Verify Scripts

```bash
# Check script file sizes
aws s3 ls s3://${BUCKET_NAME}/scripts/ --human-readable

# Expected sizes:
# glue_job_wrapper_s3.py: ~11 KB
# schema_evolution_agent_s3.py: ~18 KB
# agent_config.py: ~365 bytes
```

### Test S3 Read Access

```python
import boto3
import pandas as pd
from io import StringIO

s3_client = boto3.client('s3')
bucket = 'your-company-dq-pipeline'

# Test reading config CSV
response = s3_client.get_object(Bucket=bucket, Key='control/config/framework_inbound_config.csv')
csv_content = response['Body'].read().decode('utf-8')
df = pd.read_csv(StringIO(csv_content))
print(f"Loaded {len(df)} source configurations")

# Test reading rules CSV
response = s3_client.get_object(Bucket=bucket, Key='control/rules/dq_rule_catalog.csv')
csv_content = response['Body'].read().decode('utf-8')
df = pd.read_csv(StringIO(csv_content))
print(f"Loaded {len(df)} DQ rules")
```

---

## Key Differences from Redshift Version

| Aspect | Old (Redshift) | New (S3 Files) |
|--------|----------------|----------------|
| **Configuration Storage** | Redshift tables | S3 CSV files |
| **Schema Setup** | 7 Redshift tables to create | Just upload 2 CSV files |
| **Database Connection** | Required (psycopg2) | Not needed |
| **Cost** | Redshift cluster ($$$) | S3 storage only ($) |
| **Setup Complexity** | High (SQL DDL, connections) | Low (file uploads) |
| **Logs Storage** | Redshift anomaly_log table | S3 CSV files in logs/ |
| **Script Names** | glue_job_wrapper.py | glue_job_wrapper_s3.py |
| | schema_evolution_agent.py | schema_evolution_agent_s3.py |
| **Dependencies** | boto3, pandas, psycopg2 | boto3, pandas only |

---

## AWS Glue Job Configuration

When creating the Glue job, use these S3 paths:

```json
{
  "Name": "dq-agent-s3-job",
  "Role": "AWSGlueServiceRole-DQAgent",
  "Command": {
    "Name": "glueetl",
    "ScriptLocation": "s3://your-company-dq-pipeline/scripts/glue_job_wrapper_s3.py",
    "PythonVersion": "3"
  },
  "DefaultArguments": {
    "--additional-python-modules": "pandas==2.0.0",
    "--extra-py-files": "s3://your-company-dq-pipeline/scripts/schema_evolution_agent_s3.py",
    "--source_name": "SourceOne",
    "--s3_config_bucket": "your-company-dq-pipeline",
    "--s3_config_prefix": "control/config",
    "--s3_clean_prefix": "clean",
    "--s3_quarantine_prefix": "quarantine"
  },
  "GlueVersion": "4.0"
}
```

---

## Lambda Function for Glue Invocation

```python
import boto3
import json

def lambda_handler(event, context):
    """
    Lambda function to trigger S3-based Glue job.
    
    Triggered by S3 PUT event in inbound/ folder.
    """
    glue = boto3.client('glue')
    
    # Extract S3 file info from event
    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    s3_key = event['Records'][0]['s3']['object']['key']
    s3_file_path = f"s3://{s3_bucket}/{s3_key}"
    
    # Extract source name from file name (e.g., SourceOne from SourceOne_mbr_20260826.txt)
    file_name = s3_key.split('/')[-1]
    source_name = file_name.split('_')[0]  # Adjust parsing as needed
    
    # Start Glue job
    response = glue.start_job_run(
        JobName='dq-agent-s3-job',
        Arguments={
            '--source_name': source_name,
            '--s3_inbound_file': s3_file_path,
            '--s3_config_bucket': s3_bucket,
            '--s3_config_prefix': 'control/config',
            '--s3_clean_prefix': 'clean',
            '--s3_quarantine_prefix': 'quarantine'
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Glue job started',
            'jobRunId': response['JobRunId'],
            'source': source_name,
            'file': s3_file_path
        })
    }
```

---

## Monitoring

### Check Output Files

```bash
# Check clean files
aws s3 ls s3://${BUCKET_NAME}/clean/

# Check quarantine files
aws s3 ls s3://${BUCKET_NAME}/quarantine/

# Check logs
aws s3 ls s3://${BUCKET_NAME}/logs/
```

### Download and Inspect Logs

```bash
# Download anomaly log
aws s3 cp s3://${BUCKET_NAME}/logs/anomaly_log_<runid>_<timestamp>.csv ./

# Download quarantine manifest
aws s3 cp s3://${BUCKET_NAME}/logs/quarantine_manifest_<runid>_<timestamp>.csv ./

# View in Excel/Pandas
python -c "import pandas as pd; print(pd.read_csv('anomaly_log_<runid>_<timestamp>.csv'))"
```

---

## Cost Estimate

**S3 File-Based Implementation** (much cheaper than Redshift):

| Service | Usage | Monthly Cost (est.) |
|---------|-------|---------------------|
| **S3 Storage** | 100 GB | $2.30 |
| **S3 Requests** | 10,000 PUT/GET | $0.05 |
| **Glue Jobs** | 10 runs/day × 0.1 DPU-hour | $13.20 |
| **Lambda** | 1,000 invocations | $0.20 |
| **CloudWatch Logs** | 5 GB logs | $2.50 |
| **TOTAL** | | **~$18/month** |

**Savings vs. Redshift version**: ~$200-300/month (no Redshift cluster)

---

## Troubleshooting

### Issue: "Access Denied" on S3

**Solution**: Update IAM role for Glue job:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::your-company-dq-pipeline/*",
    "arn:aws:s3:::your-company-dq-pipeline"
  ]
}
```

### Issue: "ModuleNotFoundError: No module named 'pandas'"

**Solution**: Add to Glue job parameters:

```
--additional-python-modules pandas==2.0.0
```

### Issue: CSV Files Not Loading

**Solution**: Check file paths and bucket name:

```bash
# Verify files exist
aws s3 ls s3://your-company-dq-pipeline/control/config/ --recursive
aws s3 ls s3://your-company-dq-pipeline/control/rules/ --recursive
```

---

## Summary

✅ **NO Redshift required** - All configuration in S3 CSV files  
✅ **Simple setup** - Just upload 2 config CSVs and 2 Python scripts  
✅ **Low cost** - ~$18/month vs $200-300/month with Redshift  
✅ **Easy maintenance** - Edit CSVs in Excel, re-upload to S3  
✅ **Full DQ functionality** - Deduplication, validation, quarantine, logging  

**Next Steps**: See `AWS_Deployment_Guide_S3.md` for complete deployment instructions.
