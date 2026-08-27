# AWS Deployment Guide - S3 File-Based Version
## Data Quality Agent with S3 Configuration (NO REDSHIFT)

**Version**: 2.0 (S3 File-Based)  
**Last Updated**: 2026-08-27  
**Architecture**: Simplified - No Database Required

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [S3 Bucket Setup](#s3-bucket-setup)
5. [IAM Roles and Permissions](#iam-roles-and-permissions)
6. [Upload Configuration Files](#upload-configuration-files)
7. [Create AWS Glue Job](#create-aws-glue-job)
8. [Create Lambda Trigger](#create-lambda-trigger)
9. [Testing](#testing)
10. [Monitoring](#monitoring)
11. [Cost Optimization](#cost-optimization)
12. [Troubleshooting](#troubleshooting)

---

## Overview

This deployment guide covers the **S3 file-based** implementation of the Data Quality Agent.

### Key Advantages over Redshift Version

| Feature | S3 File-Based (This Version) | Redshift-Based (Old) |
|---------|----------------------------|----------------------|
| **Setup Complexity** | ⭐ Simple (file uploads) | ⭐⭐⭐⭐ Complex (7 tables, connections) |
| **Monthly Cost** | $15-20 | $200-300 |
| **Database Required** | ❌ No | ✅ Yes (Redshift cluster) |
| **Configuration Edits** | Edit CSV in Excel, re-upload | SQL UPDATE statements |
| **Dependencies** | boto3, pandas | boto3, pandas, psycopg2 |
| **Maintenance** | ⭐ Low | ⭐⭐⭐ Medium |

---

## Architecture

```
┌─────────────────┐
│   Data Source   │
│   (Inbound)     │
└────────┬────────┘
         │ Upload file
         ▼
┌─────────────────┐
│   S3 Inbound/   │◄────── S3 PUT Event
│   Folder        │
└────────┬────────┘
         │ Trigger
         ▼
┌─────────────────┐
│ Lambda Function │
│ (File Parser)   │
└────────┬────────┘
         │ Start Job
         ▼
┌─────────────────────────────────────────┐
│         AWS Glue Job                    │
│  ┌───────────────────────────────────┐  │
│  │ 1. Read Config from S3 CSV        │  │
│  │ 2. Read Rules from S3 CSV         │  │
│  │ 3. Load Inbound Data              │  │
│  │ 4. Detect Schema Changes          │  │
│  │ 5. Detect Duplicates              │  │
│  │ 6. Apply DQ Rules                 │  │
│  │ 7. Make Quarantine Decision       │  │
│  │ 8. Write Clean/Quarantine to S3   │  │
│  │ 9. Write Logs to S3               │  │
│  └───────────────────────────────────┘  │
└─────────┬──────────────┬────────────────┘
          │              │
          ▼              ▼
  ┌──────────────┐  ┌──────────────┐
  │ S3 Clean/    │  │ S3 Logs/     │
  │ Quarantine/  │  │              │
  └──────────────┘  └──────────────┘
```

### Data Flow

1. **Inbound File Arrives** → S3 inbound/ folder
2. **Lambda Triggered** → Parses file name, extracts source
3. **Glue Job Starts** → Reads config CSVs from S3
4. **DQ Processing** → Validates, deduplicates, quarantines
5. **Output Files** → Clean data to clean/, bad data to quarantine/
6. **Logs Written** → Anomaly logs and manifests to logs/

---

## Prerequisites

- AWS Account with admin access
- AWS CLI installed and configured
- Local repository cloned: `E:\mygit\mysvcagt`
- S3 bucket name decided (e.g., `my-company-dq-pipeline`)

---

## S3 Bucket Setup

### Step 1: Create S3 Bucket

```bash
# Set variables
export BUCKET_NAME="my-company-dq-pipeline"
export AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://${BUCKET_NAME} --region ${AWS_REGION}

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled

# Enable encryption (recommended)
aws s3api put-bucket-encryption \
    --bucket ${BUCKET_NAME} \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'
```

### Step 2: Create Folder Structure

```bash
# Create folders
aws s3api put-object --bucket ${BUCKET_NAME} --key inbound/
aws s3api put-object --bucket ${BUCKET_NAME} --key clean/
aws s3api put-object --bucket ${BUCKET_NAME} --key quarantine/
aws s3api put-object --bucket ${BUCKET_NAME} --key logs/
aws s3api put-object --bucket ${BUCKET_NAME} --key control/config/
aws s3api put-object --bucket ${BUCKET_NAME} --key control/rules/
aws s3api put-object --bucket ${BUCKET_NAME} --key scripts/
aws s3api put-object --bucket ${BUCKET_NAME} --key temp/

# Verify structure
aws s3 ls s3://${BUCKET_NAME}/
```

### Step 3: Configure Lifecycle Policy (Optional)

```bash
# Create lifecycle policy JSON
cat > lifecycle-policy.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldQuarantineFiles",
      "Status": "Enabled",
      "Prefix": "quarantine/",
      "Expiration": {
        "Days": 90
      }
    },
    {
      "Id": "DeleteOldLogs",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Expiration": {
        "Days": 30
      }
    },
    {
      "Id": "TransitionInboundToIA",
      "Status": "Enabled",
      "Prefix": "inbound/",
      "Transitions": [
        {
          "Days": 7,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
EOF

# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket ${BUCKET_NAME} \
    --lifecycle-configuration file://lifecycle-policy.json
```

---

## IAM Roles and Permissions

### Step 1: Create Glue Service Role

```bash
# Create trust policy for Glue
cat > glue-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
    --role-name DQAgentGlueRole \
    --assume-role-policy-document file://glue-trust-policy.json

# Attach AWS managed Glue policy
aws iam attach-role-policy \
    --role-name DQAgentGlueRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole
```

### Step 2: Create S3 Access Policy

```bash
# Create S3 access policy
cat > glue-s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}/*",
        "arn:aws:s3:::${BUCKET_NAME}"
      ]
    }
  ]
}
EOF

# Create and attach policy
aws iam put-role-policy \
    --role-name DQAgentGlueRole \
    --policy-name DQAgentS3Access \
    --policy-document file://glue-s3-policy.json
```

### Step 3: Create Lambda Execution Role

```bash
# Create trust policy for Lambda
cat > lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
    --role-name DQAgentLambdaRole \
    --assume-role-policy-document file://lambda-trust-policy.json

# Attach managed policies
aws iam attach-role-policy \
    --role-name DQAgentLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create Glue start job policy
cat > lambda-glue-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:StartJobRun",
        "glue:GetJobRun"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/inbound/*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name DQAgentLambdaRole \
    --policy-name DQAgentGlueStart \
    --policy-document file://lambda-glue-policy.json
```

---

## Upload Configuration Files

### Step 1: Upload Config CSVs to S3

```bash
# Navigate to local repo
cd E:\mygit\mysvcagt

# Upload framework config
aws s3 cp control/config/framework_inbound_config.csv \
    s3://${BUCKET_NAME}/control/config/framework_inbound_config.csv

# Upload DQ rules
aws s3 cp control/rules/dq_rule_catalog.csv \
    s3://${BUCKET_NAME}/control/rules/dq_rule_catalog.csv

# Verify uploads
aws s3 ls s3://${BUCKET_NAME}/control/config/
aws s3 ls s3://${BUCKET_NAME}/control/rules/
```

### Step 2: Upload Glue Scripts

```bash
# Upload S3-based Glue job wrapper
aws s3 cp scripts/glue_job_wrapper_s3.py \
    s3://${BUCKET_NAME}/scripts/glue_job_wrapper_s3.py

# Upload S3-based agent
aws s3 cp scripts/schema_evolution_agent_s3.py \
    s3://${BUCKET_NAME}/scripts/schema_evolution_agent_s3.py

# Verify uploads
aws s3 ls s3://${BUCKET_NAME}/scripts/
```

---

## Create AWS Glue Job

### Step 1: Create Glue Job via CLI

```bash
# Get IAM role ARN
GLUE_ROLE_ARN=$(aws iam get-role --role-name DQAgentGlueRole --query 'Role.Arn' --output text)

# Create Glue job
aws glue create-job \
    --name "dq-agent-s3-job" \
    --role "${GLUE_ROLE_ARN}" \
    --command Name=glueetl,ScriptLocation=s3://${BUCKET_NAME}/scripts/glue_job_wrapper_s3.py,PythonVersion=3 \
    --default-arguments '{
        "--additional-python-modules":"pandas==2.0.0,python-dateutil",
        "--extra-py-files":"s3://'${BUCKET_NAME}'/scripts/schema_evolution_agent_s3.py",
        "--enable-metrics":"true",
        "--enable-continuous-cloudwatch-log":"true",
        "--enable-spark-ui":"true",
        "--spark-event-logs-path":"s3://'${BUCKET_NAME}'/temp/spark-logs/"
    }' \
    --glue-version "4.0" \
    --max-retries 0 \
    --timeout 60 \
    --number-of-workers 2 \
    --worker-type "G.1X"

echo "Glue job created successfully"
```

### Step 2: Verify Glue Job

```bash
# List Glue jobs
aws glue get-job --job-name dq-agent-s3-job
```

---

## Create Lambda Trigger

### Step 1: Create Lambda Function

```bash
# Create Lambda deployment package
mkdir -p lambda-package
cd lambda-package

# Create lambda function code
cat > lambda_function.py <<'EOF'
import boto3
import json
import urllib.parse

def lambda_handler(event, context):
    """
    Lambda function to trigger S3-based Glue job.
    Triggered by S3 PUT event in inbound/ folder.
    """
    glue = boto3.client('glue')
    
    try:
        # Extract S3 file info from event
        s3_bucket = event['Records'][0]['s3']['bucket']['name']
        s3_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        s3_file_path = f"s3://{s3_bucket}/{s3_key}"
        
        # Extract source name from file name (e.g., SourceOne from SourceOne_mbr_20260826.txt)
        file_name = s3_key.split('/')[-1]
        source_name = file_name.split('_')[0]
        
        print(f"Processing file: {s3_file_path}, Source: {source_name}")
        
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
        
        print(f"Glue job started successfully: {response['JobRunId']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Glue job started',
                'jobRunId': response['JobRunId'],
                'source': source_name,
                'file': s3_file_path
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
EOF

# Create ZIP package
zip lambda-package.zip lambda_function.py

# Get Lambda role ARN
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name DQAgentLambdaRole --query 'Role.Arn' --output text)

# Create Lambda function
aws lambda create-function \
    --function-name dq-agent-trigger \
    --runtime python3.11 \
    --role ${LAMBDA_ROLE_ARN} \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda-package.zip \
    --timeout 60 \
    --memory-size 256

cd ..
```

### Step 2: Add S3 Trigger to Lambda

```bash
# Add permission for S3 to invoke Lambda
aws lambda add-permission \
    --function-name dq-agent-trigger \
    --principal s3.amazonaws.com \
    --statement-id s3-trigger \
    --action lambda:InvokeFunction \
    --source-arn arn:aws:s3:::${BUCKET_NAME} \
    --source-account $(aws sts get-caller-identity --query Account --output text)

# Create S3 event notification
cat > s3-notification.json <<EOF
{
  "LambdaFunctionConfigurations": [
    {
      "Id": "dq-agent-trigger",
      "LambdaFunctionArn": "$(aws lambda get-function --function-name dq-agent-trigger --query 'Configuration.FunctionArn' --output text)",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "inbound/"
            },
            {
              "Name": "suffix",
              "Value": ".txt"
            }
          ]
        }
      }
    }
  ]
}
EOF

# Apply notification configuration
aws s3api put-bucket-notification-configuration \
    --bucket ${BUCKET_NAME} \
    --notification-configuration file://s3-notification.json

echo "Lambda trigger configured successfully"
```

---

## Testing

### Test 1: Upload Sample File

```bash
# Upload test file
cd E:\mygit\mysvcagt
aws s3 cp inbound/SourceOne_mbr_20260826.txt \
    s3://${BUCKET_NAME}/inbound/SourceOne_mbr_20260826.txt

# This should automatically trigger:
# 1. Lambda function
# 2. Glue job
# 3. DQ processing
# 4. Output files in clean/ or quarantine/
```

### Test 2: Check Glue Job Execution

```bash
# List recent Glue job runs
aws glue get-job-runs --job-name dq-agent-s3-job --max-results 5

# Get specific job run details
JOB_RUN_ID="<from above command>"
aws glue get-job-run --job-name dq-agent-s3-job --run-id ${JOB_RUN_ID}
```

### Test 3: Check Output Files

```bash
# Check clean folder
aws s3 ls s3://${BUCKET_NAME}/clean/

# Check quarantine folder
aws s3 ls s3://${BUCKET_NAME}/quarantine/

# Check logs
aws s3 ls s3://${BUCKET_NAME}/logs/
```

### Test 4: Download and Inspect Results

```bash
# Download clean file (if exists)
aws s3 cp s3://${BUCKET_NAME}/clean/ ./ --recursive

# Download quarantine files
aws s3 cp s3://${BUCKET_NAME}/quarantine/ ./ --recursive

# Download logs
aws s3 cp s3://${BUCKET_NAME}/logs/ ./ --recursive

# Inspect CSV files
# (Open in Excel or use pandas)
```

---

## Monitoring

### CloudWatch Logs

```bash
# View Glue job logs
aws logs tail /aws-glue/jobs/output --follow

# View Lambda logs
aws logs tail /aws/lambda/dq-agent-trigger --follow
```

### CloudWatch Metrics

Create a CloudWatch dashboard to monitor:
- Glue job execution time
- Lambda invocation count
- S3 object counts by folder
- Error rates

### Alarms

```bash
# Create alarm for Glue job failures
aws cloudwatch put-metric-alarm \
    --alarm-name dq-agent-job-failures \
    --alarm-description "Alert when Glue job fails" \
    --metric-name glue.driver.aggregate.numFailedTasks \
    --namespace Glue \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanThreshold
```

---

## Cost Optimization

### Estimated Monthly Costs

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| S3 Storage | 100 GB | $2.30 |
| S3 Requests | 10,000 | $0.05 |
| Glue Jobs | 10 runs/day × 0.1 DPU-hour | $13.20 |
| Lambda | 1,000 invocations | $0.20 |
| CloudWatch | 5 GB logs | $2.50 |
| **TOTAL** | | **~$18/month** |

### Optimization Tips

1. **Glue Workers**: Use G.1X (1 worker) for small files
2. **Lifecycle Policies**: Auto-delete old quarantine/log files
3. **S3 Intelligent-Tiering**: Enable for inbound folder
4. **Log Retention**: Set CloudWatch log retention to 7-30 days
5. **Glue Job Timeout**: Set appropriate timeout to avoid long-running jobs

---

## Troubleshooting

### Issue: Glue Job Fails with "ModuleNotFoundError: No module named 'pandas'"

**Solution**: Check Glue job arguments include:
```
--additional-python-modules pandas==2.0.0
```

### Issue: "Access Denied" when reading S3 config files

**Solution**: Verify IAM role has S3 read permissions:
```bash
aws iam get-role-policy --role-name DQAgentGlueRole --policy-name DQAgentS3Access
```

### Issue: Lambda not triggering Glue job

**Solution**: Check Lambda logs:
```bash
aws logs tail /aws/lambda/dq-agent-trigger --follow
```

### Issue: Config CSV not found in S3

**Solution**: Verify files are uploaded:
```bash
aws s3 ls s3://${BUCKET_NAME}/control/config/ --recursive
aws s3 ls s3://${BUCKET_NAME}/control/rules/ --recursive
```

### Issue: Glue job runs but no output files

**Solution**: Check Glue job logs in CloudWatch:
```bash
aws logs tail /aws-glue/jobs/output --follow
```

---

## Next Steps

1. ✅ Test with sample data
2. ✅ Verify clean and quarantine outputs
3. ✅ Check anomaly logs
4. ⏩ Add more sources to config CSV
5. ⏩ Add more DQ rules to rules CSV
6. ⏩ Set up CloudWatch dashboard
7. ⏩ Configure email alerts for failures
8. ⏩ Schedule regular processing with EventBridge

---

## Appendix: Updating Configuration

### Adding a New Source

1. Edit local `control/config/framework_inbound_config.csv`
2. Add new row with source details
3. Re-upload to S3:
   ```bash
   aws s3 cp control/config/framework_inbound_config.csv \
       s3://${BUCKET_NAME}/control/config/framework_inbound_config.csv
   ```

### Adding New DQ Rules

1. Edit local `control/rules/dq_rule_catalog.csv`
2. Add new rule rows
3. Re-upload to S3:
   ```bash
   aws s3 cp control/rules/dq_rule_catalog.csv \
       s3://${BUCKET_NAME}/control/rules/dq_rule_catalog.csv
   ```

### No Code Changes Needed!

Configuration changes take effect immediately - no Glue job redeployment required.

---

**End of Deployment Guide**
