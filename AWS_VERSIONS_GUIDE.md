# AWS Implementation Versions - Quick Guide

## Two Versions Available

This repository contains **two complete AWS implementations** of the Data Quality Agent:

### 🆕 **Version 2.0: S3 File-Based (RECOMMENDED)**
- ✅ **Simpler setup** - No database required
- ✅ **Lower cost** - ~$18/month (vs $200-300/month)
- ✅ **Easy maintenance** - Edit CSVs in Excel, upload to S3
- ✅ **No Redshift** - All configuration in S3 CSV files

**Files:**
- `scripts/glue_job_wrapper_s3.py`
- `scripts/schema_evolution_agent_s3.py`
- `AWS_Deployment_Guide_S3.md`
- `AWS_S3_UPLOAD_MAPPING_V2.md`

### 📦 **Version 1.0: Redshift-Based (Legacy)**
- ⚠️ **Complex setup** - 7 Redshift tables to create
- ⚠️ **Higher cost** - $200-300/month for Redshift cluster
- ⚠️ **Database management** - SQL updates for config changes
- ✅ **Advanced features** - Chatbot, recommendations, full audit trail

**Files:**
- `scripts/glue_job_wrapper.py`
- `scripts/schema_evolution_agent.py`
- `scripts/dataops_chatbot.py`
- `AWS_Deployment_Guide.md`
- `AWS_S3_UPLOAD_MAPPING.md`

---

## Which Version Should I Use?

### Use **S3 File-Based (v2.0)** if:
- ✅ You want simple, low-cost solution
- ✅ You're starting fresh
- ✅ CSV files are sufficient for your needs
- ✅ You don't need advanced chatbot features
- ✅ Budget is a concern

### Use **Redshift-Based (v1.0)** if:
- ✅ You need SQL query access to configs
- ✅ You want LLM-powered chatbot
- ✅ You need rule recommendations
- ✅ You have existing Redshift infrastructure
- ✅ You need complex audit trail queries

---

## Quick Comparison

| Feature | S3 File-Based (v2.0) | Redshift-Based (v1.0) |
|---------|----------------------|------------------------|
| **Setup Time** | 30 minutes | 2-3 hours |
| **Monthly Cost** | ~$18 | ~$250 |
| **Database Required** | ❌ No | ✅ Yes (Redshift) |
| **Config Storage** | S3 CSV files | Redshift tables |
| **Config Updates** | Edit CSV, re-upload | SQL UPDATE statements |
| **Dependencies** | boto3, pandas | boto3, pandas, psycopg2 |
| **Chatbot** | ❌ No | ✅ Yes |
| **Rule Recommendations** | ❌ No | ✅ Yes |
| **Deduplication** | ✅ Yes | ✅ Yes |
| **DQ Validation** | ✅ Yes | ✅ Yes |
| **Quarantine Logic** | ✅ Yes | ✅ Yes |
| **Anomaly Logging** | ✅ Yes (CSV) | ✅ Yes (Table) |
| **Schema Evolution** | ✅ Yes | ✅ Yes |

---

## File Mapping

### S3 File-Based Version (v2.0)

```
Local                                    →  S3 Destination
=====================================    →  ========================================
control/config/*.csv                     →  s3://bucket/control/config/*.csv
control/rules/*.csv                      →  s3://bucket/control/rules/*.csv
scripts/glue_job_wrapper_s3.py           →  s3://bucket/scripts/glue_job_wrapper_s3.py
scripts/schema_evolution_agent_s3.py     →  s3://bucket/scripts/schema_evolution_agent_s3.py
```

### Redshift-Based Version (v1.0)

```
Local                                    →  AWS Destination
=====================================    →  ========================================
control/config/*.csv                     →  Load into Redshift framework_inbound_config table
control/rules/*.csv                      →  Load into Redshift dq_rule_catalog table
scripts/glue_job_wrapper.py              →  s3://bucket/scripts/glue_job_wrapper.py
scripts/schema_evolution_agent.py        →  s3://bucket/scripts/schema_evolution_agent.py
scripts/dataops_chatbot.py               →  s3://bucket/scripts/dataops_chatbot.py
```

---

## Getting Started

### For S3 File-Based (v2.0) - RECOMMENDED

1. **Read the deployment guide:**
   ```
   AWS_Deployment_Guide_S3.md
   ```

2. **Upload configuration files:**
   ```bash
   aws s3 cp control/config/framework_inbound_config.csv s3://bucket/control/config/
   aws s3 cp control/rules/dq_rule_catalog.csv s3://bucket/control/rules/
   ```

3. **Upload scripts:**
   ```bash
   aws s3 cp scripts/glue_job_wrapper_s3.py s3://bucket/scripts/
   aws s3 cp scripts/schema_evolution_agent_s3.py s3://bucket/scripts/
   ```

4. **Create Glue job:**
   ```bash
   aws glue create-job --name dq-agent-s3-job \
       --role DQAgentGlueRole \
       --command ScriptLocation=s3://bucket/scripts/glue_job_wrapper_s3.py
   ```

5. **Test:**
   ```bash
   aws s3 cp inbound/SourceOne_mbr_20260826.txt s3://bucket/inbound/
   ```

**Total setup time: ~30 minutes**

### For Redshift-Based (v1.0)

1. **Read the deployment guide:**
   ```
   AWS_Deployment_Guide.md
   ```

2. **Create Redshift cluster** (see guide)

3. **Create 7 Redshift tables** (see guide for SQL)

4. **Load configuration data into Redshift:**
   ```sql
   COPY framework_inbound_config FROM 's3://...'
   COPY dq_rule_catalog FROM 's3://...'
   ```

5. **Upload scripts:**
   ```bash
   aws s3 cp scripts/glue_job_wrapper.py s3://bucket/scripts/
   aws s3 cp scripts/schema_evolution_agent.py s3://bucket/scripts/
   ```

6. **Create Glue job with Redshift connection** (see guide)

**Total setup time: 2-3 hours**

---

## Local Development

Both versions use the same local development setup:

```bash
# Navigate to repo
cd E:\mygit\mysvcagt

# Install dependencies
pip install -r requirements.txt

# Test locally (uses CSV files)
cd scripts
python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne

# View results
dir ..\clean\
dir ..\quarantine\
dir ..\logs\
```

The local version (`dq_agent_local.py`) works the same way as the S3 file-based version, reading from CSV files.

---

## Migration Between Versions

### From v1.0 (Redshift) to v2.0 (S3 Files)

1. **Export Redshift configs to CSV:**
   ```sql
   UNLOAD ('SELECT * FROM framework_inbound_config')
   TO 's3://bucket/control/config/framework_inbound_config.csv'
   WITH CSV HEADER;
   
   UNLOAD ('SELECT * FROM dq_rule_catalog')
   TO 's3://bucket/control/rules/dq_rule_catalog.csv'
   WITH CSV HEADER;
   ```

2. **Update Glue job** to use S3-based scripts

3. **Delete Redshift cluster** (saves $200-300/month)

### From v2.0 (S3 Files) to v1.0 (Redshift)

1. **Create Redshift cluster**

2. **Create Redshift tables** (see `AWS_Deployment_Guide.md`)

3. **Load S3 CSVs into Redshift:**
   ```sql
   COPY framework_inbound_config FROM 's3://bucket/control/config/framework_inbound_config.csv'
   COPY dq_rule_catalog FROM 's3://bucket/control/rules/dq_rule_catalog.csv'
   ```

4. **Update Glue job** to use Redshift-based scripts

---

## Documentation Files

| File | Version | Description |
|------|---------|-------------|
| `README.md` | Both | Main readme with local setup |
| `AWS_Deployment_Guide_S3.md` | v2.0 | S3 file-based deployment |
| `AWS_S3_UPLOAD_MAPPING_V2.md` | v2.0 | S3 file mapping |
| `AWS_Deployment_Guide.md` | v1.0 | Redshift-based deployment |
| `AWS_S3_UPLOAD_MAPPING.md` | v1.0 | Redshift file mapping |
| `MIGRATION_GUIDE.md` | Both | Account migration guide |
| `VSCODE_SETUP_GUIDE.md` | Both | VS Code Git workflow |

---

## Support

For questions or issues:
1. Check the appropriate deployment guide
2. Review troubleshooting sections
3. Check CloudWatch logs
4. Verify IAM permissions
5. Ensure S3 bucket permissions are correct

---

## Recommendation

**For most use cases, we recommend the S3 File-Based version (v2.0):**
- ✅ Simpler to set up and maintain
- ✅ Much lower cost
- ✅ Easier to understand and troubleshoot
- ✅ Same core DQ functionality

Only use the Redshift version if you specifically need the database features (SQL queries, chatbot, recommendations).

---

**Happy Data Quality Processing! 🎉**
