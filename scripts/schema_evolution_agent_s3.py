"""
Agentic ELT Quality and Schema Evolution Agent - S3 File-Based Version
Core engine for schema validation, deduplication, quarantine routing, and anomaly logging.
Designed for AWS Glue execution with S3 CSV files for configuration (no Redshift dependency).
"""

import json
import logging
import pandas as pd
import boto3
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from io import StringIO


class SchemaEvolutionAgentS3:
    """
    Main agent for data quality, schema evolution, and controlled quarantine decisions.
    Uses S3 CSV files for configuration instead of Redshift tables.
    """

    def __init__(self, s3_config_bucket: str, s3_config_prefix: str, logger: logging.Logger):
        """
        Initialize agent with S3 configuration and logger.
        
        Args:
            s3_config_bucket: S3 bucket containing configuration files
            s3_config_prefix: Prefix/folder in S3 bucket for config files (e.g., 'control/config/')
            logger: Logger instance for audit/anomaly events
        """
        self.s3_config_bucket = s3_config_bucket
        self.s3_config_prefix = s3_config_prefix.rstrip('/')
        self.logger = logger
        self.s3_client = boto3.client('s3')
        self.run_id = None
        self.source_config = None
        self.dq_rules = []
        self.anomalies = []
        self.quarantine_decisions = []

    def _read_s3_csv(self, s3_key: str) -> pd.DataFrame:
        """
        Read CSV file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            DataFrame with CSV contents
        """
        try:
            self.logger.info(f"Reading S3 file: s3://{self.s3_config_bucket}/{s3_key}")
            response = self.s3_client.get_object(Bucket=self.s3_config_bucket, Key=s3_key)
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            self.logger.info(f"Successfully read {len(df)} rows from {s3_key}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to read S3 file {s3_key}: {e}")
            raise

    def _write_s3_csv(self, df: pd.DataFrame, s3_key: str):
        """
        Write DataFrame to S3 as CSV.
        
        Args:
            df: DataFrame to write
            s3_key: S3 object key
        """
        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            self.s3_client.put_object(
                Bucket=self.s3_config_bucket,
                Key=s3_key,
                Body=csv_buffer.getvalue()
            )
            self.logger.info(f"Written {len(df)} rows to s3://{self.s3_config_bucket}/{s3_key}")
        except Exception as e:
            self.logger.error(f"Failed to write S3 file {s3_key}: {e}")
            raise

    def load_source_config(self, source_name: str) -> Dict:
        """
        Read inbound file configuration from S3 CSV file.
        
        Args:
            source_name: Source identifier
            
        Returns:
            Configuration dict for the source
        """
        try:
            # Read framework_inbound_config.csv from S3
            config_key = f"{self.s3_config_prefix}/framework_inbound_config.csv"
            config_df = self._read_s3_csv(config_key)
            
            # Filter for the specific source
            source_rows = config_df[config_df['source_name'] == source_name]
            if source_rows.empty:
                raise ValueError(f"Source configuration not found: {source_name}")
            
            # Convert first row to dict
            config = source_rows.iloc[0].to_dict()
            
            # Parse JSON fields
            json_fields = ['business_keys', 'critical_columns', 'expected_schema']
            for field in json_fields:
                if field in config and isinstance(config[field], str):
                    config[field] = json.loads(config[field])
            
            self.source_config = config
            self.logger.info(f"Loaded config for source: {source_name}")
            return self.source_config
        except Exception as e:
            self.logger.error(f"Failed to load source config: {e}")
            raise

    def load_dq_rules(self, source_name: str) -> List[Dict]:
        """
        Load data quality rules from S3 CSV file.
        
        Args:
            source_name: Source identifier
            
        Returns:
            List of active DQ rules for the source
        """
        try:
            # Read dq_rule_catalog.csv from S3
            rules_key = f"{self.s3_config_prefix}/dq_rule_catalog.csv"
            rules_df = self._read_s3_csv(rules_key)
            
            # Filter for the specific source and active rules
            source_rules = rules_df[
                (rules_df['source_name'] == source_name) & 
                (rules_df['is_active'] == True)
            ]
            
            # Convert to list of dicts
            rules = []
            for _, row in source_rules.iterrows():
                rule = row.to_dict()
                # Parse rule_definition JSON
                if 'rule_definition' in rule and isinstance(rule['rule_definition'], str):
                    rule['rule_definition'] = json.loads(rule['rule_definition'])
                rules.append(rule)
            
            self.dq_rules = rules
            self.logger.info(f"Loaded {len(self.dq_rules)} active DQ rules for {source_name}")
            return self.dq_rules
        except Exception as e:
            self.logger.error(f"Failed to load DQ rules: {e}")
            raise

    def write_anomaly_log(self, anomaly_type: str, severity: str, column_name: str = None, 
                         action_taken: str = None, details: Dict = None, row_data: Dict = None):
        """
        Write anomaly log entry to S3 CSV file.
        
        Args:
            anomaly_type: Type of anomaly (duplicate, dq_violation, schema_drift, etc.)
            severity: Severity level (critical, high, medium, low)
            column_name: Column involved in anomaly
            action_taken: Action taken (quarantined_row, quarantined_file, etc.)
            details: Additional details as dict
            row_data: Full row data if applicable
        """
        try:
            log_entry = {
                'run_id': self.run_id,
                'source_name': self.source_config.get('source_name'),
                'file_name': self.source_config.get('current_file_name', ''),
                'anomaly_type': anomaly_type,
                'severity': severity,
                'column_name': column_name or '',
                'action_taken': action_taken or '',
                'details': json.dumps(details) if details else '',
                'row_data': json.dumps(row_data) if row_data else '',
                'detected_at': datetime.now().isoformat(),
                'resolved': False
            }
            
            self.anomalies.append(log_entry)
            self.logger.info(f"Logged anomaly: {anomaly_type} - {severity}")
        except Exception as e:
            self.logger.error(f"Failed to log anomaly: {e}")

    def detect_schema_changes(self, current_schema: Dict, expected_schema: Dict) -> Dict:
        """
        Detect schema changes: added, removed, renamed, or type-changed columns.
        
        Args:
            current_schema: Current file schema
            expected_schema: Expected/registered schema
            
        Returns:
            Dict with added_columns, removed_columns, type_changes
        """
        changes = {
            "added_columns": [],
            "removed_columns": [],
            "type_changes": []
        }
        
        current_cols = set(current_schema.keys())
        expected_cols = set(expected_schema.keys())
        
        # Detect new columns
        changes["added_columns"] = list(current_cols - expected_cols)
        
        # Detect removed columns
        changes["removed_columns"] = list(expected_cols - current_cols)
        
        # Detect type changes
        for col in current_cols & expected_cols:
            if current_schema[col] != expected_schema[col]:
                changes["type_changes"].append({
                    "column": col,
                    "expected_type": expected_schema[col],
                    "current_type": current_schema[col]
                })
        
        if any(changes.values()):
            self.logger.warning(f"Schema changes detected: {changes}")
        else:
            self.logger.info("No schema changes detected")
        
        return changes

    def detect_duplicates(self, df: pd.DataFrame, business_keys: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Detect and isolate duplicate records using business keys.
        
        Args:
            df: Data frame
            business_keys: Columns defining business uniqueness
            
        Returns:
            (clean_df, duplicates_df)
        """
        try:
            if not business_keys:
                self.logger.warning("No business keys configured for duplicate detection")
                return df, pd.DataFrame()

            # Mark duplicates (keep first occurrence)
            df['_is_duplicate'] = df.duplicated(subset=business_keys, keep='first')
            
            duplicates_df = df[df['_is_duplicate'] == True].copy()
            clean_df = df[df['_is_duplicate'] == False].copy()
            
            # Remove internal column
            clean_df = clean_df.drop(columns=['_is_duplicate'])
            duplicates_df = duplicates_df.drop(columns=['_is_duplicate'])

            self.logger.info(
                f"Duplicate detection: found {len(duplicates_df)} duplicate records, "
                f"keeping {len(clean_df)} unique records"
            )

            # Log each duplicate
            for _, dup_row in duplicates_df.iterrows():
                self.write_anomaly_log(
                    anomaly_type="duplicate",
                    severity="medium",
                    action_taken="quarantined_row",
                    row_data=dup_row.to_dict()
                )

            return clean_df, duplicates_df
        except Exception as e:
            self.logger.error(f"Duplicate detection failed: {e}")
            raise

    def validate_record_quality(self, row: pd.Series, rules: List[Dict]) -> List[Dict]:
        """
        Validate a record against quality rules.
        
        Args:
            row: Single row/record as pandas Series
            rules: List of rule definitions
            
        Returns:
            List of violations (empty if no violations)
        """
        violations = []
        for rule in rules:
            try:
                column_name = rule.get('column_name')
                rule_def = rule.get('rule_definition', {})
                operator = rule_def.get('operator')
                
                # Check null values
                if operator == 'NOT_NULL':
                    if pd.isna(row.get(column_name)) or str(row.get(column_name, '')).strip() == '':
                        violations.append({
                            'rule_id': rule.get('rule_id'),
                            'rule_name': rule.get('rule_name'),
                            'column': column_name,
                            'severity': rule.get('severity', 'medium'),
                            'message': f"NULL value found in {column_name}"
                        })
                
                # Check date format
                elif operator == 'DATE_FORMAT':
                    value = str(row.get(column_name, ''))
                    if value and not pd.isna(row.get(column_name)):
                        date_format = rule_def.get('format', 'yyyy-MM-dd')
                        try:
                            # Convert Java date format to Python format
                            py_format = date_format.replace('yyyy', '%Y').replace('MM', '%m').replace('dd', '%d')
                            datetime.strptime(value, py_format)
                        except:
                            violations.append({
                                'rule_id': rule.get('rule_id'),
                                'rule_name': rule.get('rule_name'),
                                'column': column_name,
                                'severity': rule.get('severity', 'medium'),
                                'message': f"Invalid date format in {column_name}: {value}"
                            })
                
            except Exception as e:
                self.logger.warning(f"Rule evaluation failed for {rule.get('rule_name')}: {e}")
        
        return violations

    def apply_dq_validation(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply data quality validation to all records.
        
        Args:
            df: Input DataFrame
            
        Returns:
            (clean_df, bad_df)
        """
        try:
            clean_records = []
            bad_records = []
            
            for idx, row in df.iterrows():
                violations = self.validate_record_quality(row, self.dq_rules)
                
                if violations:
                    # Add violations to row
                    row_dict = row.to_dict()
                    row_dict['_violations'] = json.dumps(violations)
                    bad_records.append(row_dict)
                    
                    # Log each violation
                    for violation in violations:
                        self.write_anomaly_log(
                            anomaly_type="dq_violation",
                            severity=violation['severity'],
                            column_name=violation['column'],
                            action_taken="quarantined_row",
                            details={'rule_id': violation['rule_id'], 'message': violation['message']},
                            row_data=row.to_dict()
                        )
                else:
                    clean_records.append(row.to_dict())
            
            clean_df = pd.DataFrame(clean_records) if clean_records else pd.DataFrame()
            bad_df = pd.DataFrame(bad_records) if bad_records else pd.DataFrame()
            
            self.logger.info(f"DQ validation complete: {len(clean_df)} clean, {len(bad_df)} bad records")
            return clean_df, bad_df
            
        except Exception as e:
            self.logger.error(f"DQ validation failed: {e}")
            raise

    def apply_quarantine_decision(self, clean_df: pd.DataFrame, bad_df: pd.DataFrame, 
                                 duplicates_df: pd.DataFrame) -> Dict:
        """
        Apply row-level or file-level quarantine based on thresholds.
        
        Args:
            clean_df: Clean records
            bad_df: Bad records (DQ violations)
            duplicates_df: Duplicate records
            
        Returns:
            Decision dict with action, clean_count, quarantine_count
        """
        try:
            total_records = len(clean_df) + len(bad_df) + len(duplicates_df)
            bad_records = len(bad_df) + len(duplicates_df)
            
            if total_records == 0:
                return {'action': 'skip', 'reason': 'empty_file'}
            
            bad_percent = (bad_records / total_records) * 100
            threshold = self.source_config.get('max_bad_rows_percent', 10.0)
            
            if bad_percent >= threshold:
                decision = {
                    'action': 'quarantine_file',
                    'reason': 'threshold_exceeded',
                    'bad_percent': bad_percent,
                    'threshold': threshold,
                    'total_records': total_records,
                    'clean_count': len(clean_df),
                    'quarantine_count': total_records
                }
                self.logger.warning(
                    f"File quarantine: {bad_percent:.2f}% bad records exceeds {threshold}% threshold"
                )
            else:
                decision = {
                    'action': 'quarantine_rows',
                    'reason': 'row_level_quarantine',
                    'bad_percent': bad_percent,
                    'threshold': threshold,
                    'total_records': total_records,
                    'clean_count': len(clean_df),
                    'quarantine_count': bad_records
                }
                self.logger.info(
                    f"Row-level quarantine: {bad_percent:.2f}% bad records within {threshold}% threshold"
                )
            
            self.quarantine_decisions.append(decision)
            return decision
            
        except Exception as e:
            self.logger.error(f"Quarantine decision failed: {e}")
            raise

    def finalize_run(self):
        """
        Write all anomaly logs and quarantine decisions to S3 at end of run.
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Write anomaly logs
            if self.anomalies:
                anomaly_df = pd.DataFrame(self.anomalies)
                log_key = f"logs/anomaly_log_{self.run_id}_{timestamp}.csv"
                self._write_s3_csv(anomaly_df, log_key)
                self.logger.info(f"Written {len(self.anomalies)} anomaly logs to S3")
            
            # Write quarantine manifest
            if self.quarantine_decisions:
                manifest_df = pd.DataFrame(self.quarantine_decisions)
                manifest_key = f"logs/quarantine_manifest_{self.run_id}_{timestamp}.csv"
                self._write_s3_csv(manifest_df, manifest_key)
                self.logger.info(f"Written {len(self.quarantine_decisions)} quarantine decisions to S3")
            
        except Exception as e:
            self.logger.error(f"Failed to finalize run: {e}")
            raise
