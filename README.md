# Data Quality Agent (mysvcagt)

## Overview
A data quality agent that scans incoming files, detects anomalies based on configurable DQ rules, quarantines invalid data, and produces clean files for downstream processing.

This solution supports both local file-based execution (for development/testing) and AWS cloud deployment with Redshift integration.

## Features
- **Schema Validation**: Detects schema changes, new columns, missing columns
- **Duplicate Detection**: Identifies and removes duplicate records based on business keys
- **Data Quality Rules**: Validates records against configurable DQ rules
  - Null checks
  - Type validation
  - Date format validation
  - Custom rule definitions
- **Intelligent Quarantine**: 
  - Row-level quarantine for individual bad records
  - Full file quarantine when bad record threshold is exceeded
- **Comprehensive Logging**: Detailed error logs with violation details
- **Clean Data Output**: Produces clean files ready for downstream processing

## Folder Structure
```
mysvcagt/
├── inbound/              # Incoming data files to be processed
├── clean/                # Clean data files (output)
├── quarantine/           # Quarantined bad records
├── control/
│   ├── config/
│   │   └── framework_inbound_config.csv    # Source configuration
│   └── rules/
│       └── dq_rule_catalog.csv            # Data quality rules
├── scripts/
│   ├── dq_agent_local.py                  # Local file-based agent
│   ├── glue_job_wrapper.py                # AWS Glue job wrapper
│   ├── schema_evolution_agent.py          # Core agent (Redshift-based)
│   └── dataops_chatbot.py                 # LLM-powered query interface
└── logs/                 # Processing and error logs
```

## Configuration Files

### 1. framework_inbound_config.csv
Defines source configuration including:
- Source name and file pattern
- S3 paths (for AWS deployment)
- Business keys for deduplication
- Critical columns
- Expected schema
- Quarantine policies
- Feature flags (deduplication, schema check, anomaly detection)

### 2. dq_rule_catalog.csv
Defines data quality rules:
- Rule name and type
- Source and column mapping
- Rule definition (JSON)
- Severity level (critical, high, medium, low)
- Enabled flag

## Local Execution

### Prerequisites
```bash
# Python 3.8 or higher
python --version

# Install dependencies
pip install -r requirements.txt
```

### Running the Agent
```bash
cd E:\mygit\mysvcagt\scripts

# Syntax
python dq_agent_local.py <filename> <source_name>

# Example
python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne
```

### Sample Test
```bash
# Process the sample file
python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne

# Expected output:
# - Clean records written to: clean/SourceOne_mbr_20260826.txt
# - Bad records written to: quarantine/SourceOne_mbr_20260826_<timestamp>_quarantine.csv
# - Errors logged to: logs/error_log_<date>.csv
# - Processing log: logs/dq_agent_<date>.log
```

## Output Files

### Clean File (clean/)
- Contains only records that passed all DQ checks
- Duplicates removed (if deduplication enabled)
- Same format as input file
- Ready for downstream processing

### Quarantine File (quarantine/)
- Contains records that failed DQ checks
- Includes 'violations' column with detailed error information
- Includes duplicate records (if deduplication enabled)
- Timestamped for traceability

### Error Log (logs/)
- **error_log_YYYYMMDD.csv**: Detailed violation log
  - Source file, row index, rule name
  - Column name, severity, violation description
  - Actual value that failed validation
- **dq_agent_YYYYMMDD.log**: Processing execution log

## AWS Deployment

For AWS cloud deployment with Redshift integration, see:
- **AWS_Deployment_Guide.pdf** - Comprehensive deployment guide
- **glue_job_wrapper.py** - AWS Glue job implementation
- **schema_evolution_agent.py** - Redshift-based agent core

### Key AWS Components
- **AWS Glue**: Data processing jobs
- **Amazon S3**: File storage (inbound/clean/quarantine)
- **Amazon Redshift**: Configuration and logging database
- **MWAA (Airflow)**: Workflow orchestration
- **AWS Lambda**: Event triggers and notifications

## Data Quality Rules

### Supported Rule Types

#### null_check
Validates that required fields are populated.
```json
{
  "operator": "NOT_NULL"
}
```

#### type_check
Validates data type and format.
```json
{
  "operator": "DATE_FORMAT",
  "format": "yyyy-MM-dd"
}
```

### Adding New Rules
Edit `control/rules/dq_rule_catalog.csv`:
1. Define rule name and type
2. Specify source and column
3. Set rule definition (JSON)
4. Set severity (critical, high, medium, low)
5. Enable the rule (enabled=true)

## Quarantine Policies

### Row-Level Quarantine
- Individual bad records are removed from the file
- Bad records written to quarantine folder
- Clean records proceed to clean folder
- Applied when bad record % < threshold

### Full File Quarantine
- Entire file moved to quarantine
- No clean file produced
- Applied when bad record % >= max_bad_rows_percent
- Prevents downstream processing of severely bad files

## Troubleshooting

### No clean file generated
- Check if file exceeded bad record threshold (default 10%)
- Review quarantine folder for full file quarantine
- Check logs/dq_agent_*.log for details

### Missing configuration
- Ensure source_name exists in framework_inbound_config.csv
- Verify rules exist for the source in dq_rule_catalog.csv

### Import errors
```bash
pip install -r requirements.txt
```

## Development

### Adding a New Source
1. Add entry to `control/config/framework_inbound_config.csv`
2. Define DQ rules in `control/rules/dq_rule_catalog.csv`
3. Place sample file in `inbound/` folder
4. Run the agent with new source name

### Custom Rule Types
Extend `validate_record()` method in `dq_agent_local.py` to add new rule types:
- range_check
- pattern_match
- referential_integrity
- statistical_outlier

## License
Internal use only

## Support
For questions or issues, contact the Data Engineering team.

## Version History
- v1.0 (2026-08-26): Initial release with local file support
  - Schema validation
  - Deduplication
  - DQ rule engine
  - Quarantine management
  - Error logging
