"""
Agentic ELT Quality and Schema Evolution Agent
Core engine for schema validation, deduplication, quarantine routing, and anomaly logging.
Designed for AWS Glue execution with Postgres/Redshift persistence.
"""

import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor


class SchemaEvolutionAgent:
    """
    Main agent for data quality, schema evolution, and controlled quarantine decisions.
    """

    def __init__(self, db_config: Dict, logger: logging.Logger):
        """
        Initialize agent with database connection and logger.
        
        Args:
            db_config: Database connection parameters (host, port, database, user, password)
            logger: Logger instance for audit/anomaly events
        """
        self.db_config = db_config
        self.logger = logger
        self.conn = None
        self.cursor = None
        self.run_id = None
        self.source_config = None
        self.anomalies = []
        self.quarantine_decisions = []

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config.get("host"),
                port=self.db_config.get("port", 5432),
                database=self.db_config.get("database"),
                user=self.db_config.get("user"),
                password=self.db_config.get("password")
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def load_source_config(self, source_name: str) -> Dict:
        """
        Read inbound file configuration from framework_inbound_config table.
        
        Args:
            source_name: Source identifier
            
        Returns:
            Configuration dict for the source
        """
        try:
            query = """
                SELECT * FROM framework_inbound_config 
                WHERE source_name = %s
            """
            self.cursor.execute(query, (source_name,))
            config = self.cursor.fetchone()
            if not config:
                raise ValueError(f"Source configuration not found: {source_name}")
            self.source_config = dict(config)
            self.logger.info(f"Loaded config for source: {source_name}")
            return self.source_config
        except Exception as e:
            self.logger.error(f"Failed to load source config: {e}")
            raise

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
            "type_changes": [],
            "reordered_columns": False
        }

        current_cols = set(current_schema.keys())
        expected_cols = set(expected_schema.keys())

        changes["added_columns"] = list(current_cols - expected_cols)
        changes["removed_columns"] = list(expected_cols - current_cols)

        for col in current_cols & expected_cols:
            if current_schema[col] != expected_schema[col]:
                changes["type_changes"].append({
                    "column": col,
                    "old_type": expected_schema[col],
                    "new_type": current_schema[col]
                })

        return changes

    def handle_new_columns(self, df, new_columns: List[str], file_name: str) -> Tuple[Any, int]:
        """
        Handle new columns based on populated-row threshold.
        - If populated count < low_threshold: quarantine only affected rows
        - If populated count >= high_threshold: quarantine entire file
        - In between: apply policy from config
        
        Args:
            df: Data frame or row collection
            new_columns: List of newly detected columns
            file_name: Source file name
            
        Returns:
            (remaining_df, quarantined_count)
        """
        quarantined_count = 0
        
        for col in new_columns:
            populated_count = self._count_populated_values(df, col)
            
            low_thresh = self.source_config.get("new_column_low_threshold_count", 50)
            high_thresh = self.source_config.get("new_column_high_threshold_count", 5000)
            
            if populated_count < low_thresh:
                # Quarantine only affected rows
                self.logger.info(
                    f"New column '{col}' has {populated_count} populated values (< {low_thresh}). "
                    f"Quarantining affected rows only."
                )
                df, qc = self._quarantine_rows_with_column(df, col, file_name)
                quarantined_count += qc
            elif populated_count >= high_thresh:
                # Quarantine entire file
                self.logger.warning(
                    f"New column '{col}' has {populated_count} populated values (>= {high_thresh}). "
                    f"Quarantining entire file."
                )
                self._log_anomaly(
                    anomaly_type="schema_drift",
                    column_name=col,
                    severity="critical",
                    action_taken="quarantined_file",
                    details={"new_column_high_populated": populated_count}
                )
                return None, len(df)  # Return None to signal full-file quarantine
            else:
                # Mid-range: apply row-level quarantine per config
                self.logger.info(
                    f"New column '{col}' has {populated_count} populated values. "
                    f"Applying row-level quarantine."
                )
                df, qc = self._quarantine_rows_with_column(df, col, file_name)
                quarantined_count += qc
        
        return df, quarantined_count

    def detect_duplicates(self, df, business_keys: List[str]) -> Tuple[Any, List[Dict]]:
        """
        Detect and isolate duplicate records using business keys.
        
        Args:
            df: Data frame
            business_keys: Columns defining business uniqueness
            
        Returns:
            (clean_df, duplicates_list)
        """
        try:
            if not business_keys:
                self.logger.warning("No business keys configured for duplicate detection")
                return df, []

            duplicates = df[df.duplicated(subset=business_keys, keep=False)]
            clean_df = df.drop_duplicates(subset=business_keys, keep="first")

            self.logger.info(
                f"Duplicate detection: found {len(duplicates)} duplicate records, "
                f"keeping {len(clean_df)} unique records"
            )

            for _, dup_row in duplicates.iterrows():
                self._log_anomaly(
                    anomaly_type="duplicate",
                    business_key_hash=self._hash_business_key(dup_row, business_keys),
                    severity="medium",
                    action_taken="quarantined_row",
                    row_data=dict(dup_row)
                )

            return clean_df, duplicates.to_dict('records')
        except Exception as e:
            self.logger.error(f"Duplicate detection failed: {e}")
            raise

    def validate_record_quality(self, row: Dict, rules: List[Dict]) -> List[Dict]:
        """
        Validate a record against quality rules.
        
        Args:
            row: Single row/record
            rules: List of rule definitions
            
        Returns:
            List of violations (empty if no violations)
        """
        violations = []
        for rule in rules:
            try:
                result = self._evaluate_rule(row, rule)
                if not result["passed"]:
                    violations.append({
                        "rule_id": rule.get("rule_id"),
                        "rule_name": rule.get("rule_name"),
                        "column": rule.get("column_name"),
                        "severity": rule.get("severity", "medium"),
                        "message": result.get("message")
                    })
            except Exception as e:
                self.logger.warning(f"Rule evaluation failed: {e}")
        return violations

    def apply_quarantine_decision(
        self, 
        df, 
        file_name: str, 
        bad_rows: List[Dict],
        quarantine_reason: str
    ) -> Tuple[Any, Dict]:
        """
        Apply row-level or file-level quarantine based on thresholds and policies.
        
        Args:
            df: Data frame
            file_name: Source file
            bad_rows: List of bad records identified
            quarantine_reason: Reason for quarantine
            
        Returns:
            (clean_df, quarantine_manifest)
        """
        bad_count = len(bad_rows)
        total_count = len(df)
        bad_percent = (bad_count / total_count * 100) if total_count > 0 else 0
        max_bad_percent = self.source_config.get("max_bad_rows_percent", 5.0)

        quarantine_manifest = {
            "file_name": file_name,
            "total_rows": total_count,
            "quarantined_rows": bad_count,
            "quarantine_percent": bad_percent,
            "quarantine_level": "row",
            "reason": quarantine_reason
        }

        # File-level quarantine if threshold exceeded
        if bad_percent > max_bad_percent:
            quarantine_manifest["quarantine_level"] = "file"
            self.logger.warning(
                f"Bad record percentage ({bad_percent}%) exceeds threshold ({max_bad_percent}%). "
                f"Quarantining entire file: {file_name}"
            )
            self._log_anomaly(
                anomaly_type="data_quality_violation",
                severity="critical",
                action_taken="quarantined_file",
                details={"bad_percent": bad_percent, "threshold": max_bad_percent}
            )
            return None, quarantine_manifest

        # Row-level quarantine
        clean_df = df.drop(df[df.index.isin([r.get("_row_index") for r in bad_rows])].index)
        self.logger.info(
            f"Quarantined {bad_count} bad rows (row-level). "
            f"Processed {len(clean_df)} clean records."
        )

        return clean_df, quarantine_manifest

    def _log_anomaly(
        self, 
        anomaly_type: str, 
        severity: str = "medium",
        action_taken: str = None,
        **kwargs
    ):
        """Insert anomaly event into dq_anomaly_log."""
        try:
            query = """
                INSERT INTO dq_anomaly_log 
                (run_id, source_name, file_name, anomaly_type, severity, action_taken, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(
                query,
                (
                    self.run_id,
                    self.source_config.get("source_name", "unknown"),
                    kwargs.get("file_name", "unknown"),
                    anomaly_type,
                    severity,
                    action_taken
                )
            )
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log anomaly: {e}")

    def _hash_business_key(self, row: Dict, business_keys: List[str]) -> str:
        """Generate hash of business key values for duplicate tracking."""
        key_values = [str(row.get(k, "")) for k in business_keys]
        return hashlib.md5("".join(key_values).encode()).hexdigest()

    def _count_populated_values(self, df, column: str) -> int:
        """Count non-null values in a column."""
        return df[column].notna().sum()

    def _quarantine_rows_with_column(self, df, column: str, file_name: str) -> Tuple[Any, int]:
        """Quarantine rows where a specific column is populated."""
        quarantined = df[df[column].notna()]
        clean = df[df[column].isna()]
        self.logger.info(f"Quarantined {len(quarantined)} rows due to populated column '{column}'")
        return clean, len(quarantined)

    def _evaluate_rule(self, row: Dict, rule: Dict) -> Dict:
        """Evaluate a single quality rule against a row."""
        try:
            col = rule.get("column_name")
            rule_def = json.loads(rule.get("rule_definition", "{}"))
            value = row.get(col)

            if rule_def.get("operator") == "IS_NULL" and rule_def.get("threshold") == 0:
                if value is None:
                    return {"passed": False, "message": f"Column '{col}' is null (not allowed)"}

            return {"passed": True}
        except Exception as e:
            return {"passed": False, "message": f"Rule evaluation error: {e}"}

    def finalize_run(self):
        """Commit all anomaly logs and close connection."""
        try:
            if self.conn:
                self.conn.commit()
            self.logger.info(f"Run {self.run_id} finalized and committed")
        except Exception as e:
            self.logger.error(f"Failed to finalize run: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            self.close()


class RuleRecommendationEngine:
    """
    Learns from recurring anomalies and recommends new rules.
    """

    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=RealDictCursor)

    def analyze_anomaly_patterns(self, source_name: str, days_back: int = 30) -> List[Dict]:
        """
        Mine anomaly history and recommend rules.
        
        Args:
            source_name: Source to analyze
            days_back: Historical window
            
        Returns:
            List of recommended rule definitions
        """
        query = """
            SELECT 
                anomaly_type,
                column_name,
                COUNT(*) as frequency,
                AVG(severity) as avg_severity
            FROM dq_anomaly_log
            WHERE source_name = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
            GROUP BY anomaly_type, column_name
            HAVING COUNT(*) > 5
            ORDER BY frequency DESC
        """
        self.cursor.execute(query, (source_name, days_back))
        patterns = self.cursor.fetchall()

        recommendations = []
        for pattern in patterns:
            rec = {
                "rule_name": f"auto_{pattern['anomaly_type']}_{pattern['column_name']}",
                "rule_type": pattern["anomaly_type"],
                "column_name": pattern["column_name"],
                "source_name": source_name,
                "confidence_score": min(pattern["frequency"] / 100.0, 0.99),
                "evidence_text": f"Detected {pattern['frequency']} occurrences in {days_back} days",
                "frequency_count": pattern["frequency"]
            }
            recommendations.append(rec)

        return recommendations

    def store_recommendations(self, recommendations: List[Dict]):
        """Persist recommendations for human approval."""
        for rec in recommendations:
            try:
                query = """
                    INSERT INTO dq_rule_recommendations
                    (rule_name, rule_type, column_name, source_name, confidence_score, 
                     evidence_text, frequency_count, recommendation_status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
                    ON CONFLICT (rule_name) DO NOTHING
                """
                self.cursor.execute(
                    query,
                    (
                        rec["rule_name"],
                        rec["rule_type"],
                        rec.get("column_name"),
                        rec.get("source_name"),
                        rec.get("confidence_score"),
                        rec.get("evidence_text"),
                        rec.get("frequency_count")
                    )
                )
            except Exception as e:
                print(f"Failed to store recommendation: {e}")
        self.conn.commit()
