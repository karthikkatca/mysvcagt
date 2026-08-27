"""
Data Quality Agent - Local File-Based Version
Scans incoming files, detects anomalies, quarantines bad data, and creates clean files.
Uses CSV configuration files instead of Redshift for local testing/development.
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path
import shutil


class DataQualityAgent:
    """
    Agent for data quality validation, anomaly detection, and quarantine management.
    Uses local CSV files for configuration and logging instead of database.
    """
    
    def __init__(self, base_path: str = "E:\\mygit\\mysvcagt"):
        """
        Initialize the Data Quality Agent.
        
        Args:
            base_path: Root path for the project folders
        """
        self.base_path = Path(base_path)
        self.inbound_path = self.base_path / "inbound"
        self.clean_path = self.base_path / "clean"
        self.quarantine_path = self.base_path / "quarantine"
        self.control_path = self.base_path / "control"
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Data structures
        self.source_config = None
        self.dq_rules = []
        self.error_log = []
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the agent."""
        log_file = self.base_path / "logs" / f"dq_agent_{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger('DataQualityAgent')
    
    def load_source_config(self, source_name: str) -> Dict:
        """
        Load source configuration from CSV file.
        
        Args:
            source_name: Name of the source to process
            
        Returns:
            Configuration dictionary for the source
        """
        config_file = self.control_path / "config" / "framework_inbound_config.csv"
        
        with open(config_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['source_name'] == source_name:
                    self.source_config = row
                    # Parse JSON fields
                    self.source_config['business_keys'] = json.loads(row['business_keys'])
                    self.source_config['critical_columns'] = json.loads(row['critical_columns'])
                    self.source_config['expected_schema'] = json.loads(row['expected_schema'])
                    self.logger.info(f"Loaded configuration for source: {source_name}")
                    return self.source_config
        
        raise ValueError(f"Source configuration not found: {source_name}")
    
    def load_dq_rules(self, source_name: str) -> List[Dict]:
        """
        Load data quality rules from CSV file.
        
        Args:
            source_name: Name of the source
            
        Returns:
            List of active DQ rules for the source
        """
        rules_file = self.control_path / "rules" / "dq_rule_catalog.csv"
        
        with open(rules_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['source_name'] == source_name and row['enabled'].lower() == 'true':
                    row['rule_definition'] = json.loads(row['rule_definition'])
                    self.dq_rules.append(row)
        
        self.logger.info(f"Loaded {len(self.dq_rules)} active DQ rules for {source_name}")
        return self.dq_rules
    
    def read_inbound_file(self, file_path: Path) -> List[Dict]:
        """
        Read inbound data file.
        
        Args:
            file_path: Path to the inbound file
            
        Returns:
            List of records as dictionaries
        """
        records = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                row['_row_index'] = idx + 1
                records.append(row)
        
        self.logger.info(f"Read {len(records)} records from {file_path.name}")
        return records
    
    def validate_record(self, record: Dict, rules: List[Dict]) -> List[Dict]:
        """
        Validate a single record against DQ rules.
        
        Args:
            record: Data record to validate
            rules: List of DQ rules to apply
            
        Returns:
            List of violations found
        """
        violations = []
        
        for rule in rules:
            column_name = rule['column_name']
            rule_type = rule['rule_type']
            rule_def = rule['rule_definition']
            
            # Get column value
            value = record.get(column_name, '')
            
            # Apply rule based on type
            violation = None
            
            if rule_type == 'null_check':
                if rule_def['operator'] == 'NOT_NULL':
                    if not value or value.strip() == '':
                        violation = {
                            'row_index': record['_row_index'],
                            'rule_name': rule['rule_name'],
                            'column_name': column_name,
                            'severity': rule['severity'],
                            'rule_description': rule['rule_description'],
                            'actual_value': value,
                            'timestamp': datetime.now().isoformat()
                        }
            
            elif rule_type == 'type_check':
                if rule_def['operator'] == 'DATE_FORMAT':
                    expected_format = rule_def.get('format', 'yyyy-MM-dd')
                    if value and value.strip():
                        # Simple date validation (yyyy-MM-dd format)
                        try:
                            datetime.strptime(value, '%Y-%m-%d')
                        except ValueError:
                            violation = {
                                'row_index': record['_row_index'],
                                'rule_name': rule['rule_name'],
                                'column_name': column_name,
                                'severity': rule['severity'],
                                'rule_description': rule['rule_description'],
                                'actual_value': value,
                                'expected_format': expected_format,
                                'timestamp': datetime.now().isoformat()
                            }
            
            if violation:
                violations.append(violation)
        
        return violations
    
    def detect_duplicates(self, records: List[Dict], business_keys: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """
        Detect duplicate records based on business keys.
        
        Args:
            records: List of records
            business_keys: List of column names that form the business key
            
        Returns:
            Tuple of (unique_records, duplicate_records)
        """
        seen = {}
        unique_records = []
        duplicate_records = []
        
        for record in records:
            # Create key from business key columns
            key_values = tuple(record.get(k, '') for k in business_keys)
            
            if key_values in seen:
                duplicate_records.append(record)
                self.logger.warning(f"Duplicate detected: row {record['_row_index']}, key {key_values}")
            else:
                seen[key_values] = True
                unique_records.append(record)
        
        self.logger.info(f"Found {len(duplicate_records)} duplicate records")
        return unique_records, duplicate_records
    
    def quarantine_bad_records(self, records: List[Dict], violations_map: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Separate clean and bad records based on violations.
        
        Args:
            records: All records
            violations_map: Map of row_index to violations
            
        Returns:
            Tuple of (clean_records, bad_records)
        """
        clean_records = []
        bad_records = []
        
        for record in records:
            row_idx = record['_row_index']
            if row_idx in violations_map and violations_map[row_idx]:
                # Add violations to record for logging
                record['_violations'] = violations_map[row_idx]
                bad_records.append(record)
            else:
                clean_records.append(record)
        
        self.logger.info(f"Clean records: {len(clean_records)}, Bad records: {len(bad_records)}")
        return clean_records, bad_records
    
    def write_clean_file(self, records: List[Dict], source_file_name: str):
        """
        Write clean records to output file.
        
        Args:
            records: Clean records to write
            source_file_name: Original source file name
        """
        self.clean_path.mkdir(exist_ok=True)
        output_file = self.clean_path / source_file_name
        
        if not records:
            self.logger.warning("No clean records to write")
            return
        
        # Get fieldnames (exclude internal fields)
        fieldnames = [k for k in records[0].keys() if not k.startswith('_')]
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                # Write only data fields
                clean_record = {k: v for k, v in record.items() if not k.startswith('_')}
                writer.writerow(clean_record)
        
        self.logger.info(f"Wrote {len(records)} clean records to {output_file}")
    
    def write_quarantine_log(self, bad_records: List[Dict], source_file_name: str):
        """
        Write bad records and violations to quarantine folder.
        
        Args:
            bad_records: Records with violations
            source_file_name: Original source file name
        """
        if not bad_records:
            self.logger.info("No bad records to quarantine")
            return
        
        self.quarantine_path.mkdir(exist_ok=True)
        
        # Write quarantined data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        quarantine_file = self.quarantine_path / f"{source_file_name}_{timestamp}_quarantine.csv"
        
        # Get all fieldnames including violations
        fieldnames = [k for k in bad_records[0].keys() if not k.startswith('_')]
        fieldnames.append('violations')
        
        with open(quarantine_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in bad_records:
                row = {k: v for k, v in record.items() if not k.startswith('_')}
                # Add violations as JSON string
                if '_violations' in record:
                    row['violations'] = json.dumps(record['_violations'])
                writer.writerow(row)
        
        self.logger.info(f"Wrote {len(bad_records)} bad records to {quarantine_file}")
        
        # Also write to error log
        self._write_error_log(bad_records, source_file_name)
    
    def _write_error_log(self, bad_records: List[Dict], source_file_name: str):
        """
        Write detailed error log.
        
        Args:
            bad_records: Records with violations
            source_file_name: Original source file name
        """
        log_dir = self.base_path / "logs"
        log_dir.mkdir(exist_ok=True)
        
        error_log_file = log_dir / f"error_log_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Prepare error log entries
        error_entries = []
        for record in bad_records:
            if '_violations' in record:
                for violation in record['_violations']:
                    error_entries.append({
                        'source_file': source_file_name,
                        'row_index': violation['row_index'],
                        'rule_name': violation['rule_name'],
                        'column_name': violation['column_name'],
                        'severity': violation['severity'],
                        'rule_description': violation['rule_description'],
                        'actual_value': violation.get('actual_value', ''),
                        'timestamp': violation['timestamp']
                    })
        
        # Write or append to error log
        file_exists = error_log_file.exists()
        with open(error_log_file, 'a', newline='') as f:
            fieldnames = ['source_file', 'row_index', 'rule_name', 'column_name', 
                         'severity', 'rule_description', 'actual_value', 'timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerows(error_entries)
        
        self.logger.info(f"Logged {len(error_entries)} errors to {error_log_file}")
    
    def process_file(self, file_name: str, source_name: str):
        """
        Main processing function for a single file.
        
        Args:
            file_name: Name of the file to process
            source_name: Source name for configuration lookup
        """
        self.logger.info(f"=" * 80)
        self.logger.info(f"Starting DQ Agent processing: {file_name}")
        self.logger.info(f"=" * 80)
        
        # Load configuration and rules
        self.load_source_config(source_name)
        self.load_dq_rules(source_name)
        
        # Read inbound file
        file_path = self.inbound_path / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Inbound file not found: {file_path}")
        
        records = self.read_inbound_file(file_path)
        
        # Step 1: Detect duplicates
        if self.source_config.get('enable_deduplication', 'false').lower() == 'true':
            self.logger.info("Step 1: Deduplication check...")
            business_keys = self.source_config['business_keys']
            records, duplicates = self.detect_duplicates(records, business_keys)
            
            if duplicates:
                self.write_quarantine_log(duplicates, f"{file_name}_duplicates")
        
        # Step 2: Validate data quality
        self.logger.info("Step 2: Data quality validation...")
        violations_map = {}
        
        for record in records:
            violations = self.validate_record(record, self.dq_rules)
            if violations:
                violations_map[record['_row_index']] = violations
        
        # Step 3: Quarantine bad records
        self.logger.info("Step 3: Quarantine decision...")
        clean_records, bad_records = self.quarantine_bad_records(records, violations_map)
        
        # Calculate bad record percentage
        total_records = len(records)
        bad_percent = (len(bad_records) / total_records * 100) if total_records > 0 else 0
        max_bad_percent = float(self.source_config.get('max_bad_rows_percent', 10))
        
        self.logger.info(f"Bad record percentage: {bad_percent:.2f}% (threshold: {max_bad_percent}%)")
        
        # Check if entire file should be quarantined
        if bad_percent > max_bad_percent:
            self.logger.error(f"File quarantined: bad record threshold exceeded")
            # Move entire file to quarantine
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            quarantine_full = self.quarantine_path / f"{file_name}_{timestamp}_full_quarantine.txt"
            shutil.copy(file_path, quarantine_full)
            self.logger.info(f"Full file copied to quarantine: {quarantine_full}")
            return
        
        # Step 4: Write outputs
        self.logger.info("Step 4: Writing outputs...")
        
        if bad_records:
            self.write_quarantine_log(bad_records, file_name.replace('.txt', ''))
        
        if clean_records:
            self.write_clean_file(clean_records, file_name)
        
        self.logger.info("=" * 80)
        self.logger.info(f"Processing completed successfully")
        self.logger.info(f"Total records: {total_records}")
        self.logger.info(f"Clean records: {len(clean_records)}")
        self.logger.info(f"Bad records: {len(bad_records)}")
        self.logger.info(f"Duplicate records: {len(duplicates) if duplicates else 0}")
        self.logger.info("=" * 80)


def main():
    """Main entry point for the DQ agent."""
    if len(sys.argv) < 3:
        print("Usage: python dq_agent_local.py <file_name> <source_name>")
        print("Example: python dq_agent_local.py SourceOne_mbr_20260826.txt SourceOne")
        sys.exit(1)
    
    file_name = sys.argv[1]
    source_name = sys.argv[2]
    
    agent = DataQualityAgent()
    
    try:
        agent.process_file(file_name, source_name)
        print(f"\n[SUCCESS] Processing completed successfully!")
        print(f"  - Check 'clean' folder for clean data")
        print(f"  - Check 'quarantine' folder for bad records")
        print(f"  - Check 'logs' folder for detailed logs")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        logging.exception("Fatal error during processing")
        sys.exit(1)


if __name__ == "__main__":
    main()
