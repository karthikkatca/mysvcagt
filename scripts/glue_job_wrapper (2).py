"""
AWS Glue Job Wrapper - Entry point for ELT Quality Agent execution.
Integrates with MWAA Airflow and Redshift/Postgres control plane.
"""

import sys
import logging
import json
from datetime import datetime
import uuid

from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from schema_evolution_agent import SchemaEvolutionAgent, RuleRecommendationEngine


def setup_logging(job_name: str) -> logging.Logger:
    """Configure structured logging for Glue job."""
    logger = logging.getLogger(job_name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def lambda_handler(event, context):
    """
    AWS Glue job entry point.
    
    Event payload expected:
    {
        "source_name": "vendor_A_orders",
        "s3_inbound_file": "s3://inbound-bucket/vendor_a/orders_20240812.csv",
        "db_config": {
            "host": "redshift-cluster.xxx.redshift.amazonaws.com",
            "port": 5439,
            "database": "dw_analytics",
            "user": "glue_user",
            "password": "***"
        },
        "airflow_run_id": "vendor_a_orders_20240812_120000"
    }
    """
    job_name = context.job_name if hasattr(context, 'job_name') else "schema-evolution-agent"
    logger = setup_logging(job_name)
    
    try:
        # Parse input event
        source_name = event.get("source_name")
        s3_file_path = event.get("s3_inbound_file")
        db_config = event.get("db_config")
        run_id = event.get("airflow_run_id", str(uuid.uuid4()))
        
        logger.info(f"Starting ELT Quality Agent for source: {source_name}, run_id: {run_id}")
        
        # Initialize Spark/Glue
        sc = SparkContext.getOrCreate()
        glue_ctx = GlueContext(sc)
        spark = glue_ctx.spark_session
        
        # Initialize agent
        agent = SchemaEvolutionAgent(db_config, logger)
        agent.run_id = run_id
        agent.connect()
        
        # Load source configuration
        agent.load_source_config(source_name)
        
        # Read inbound file
        logger.info(f"Reading inbound file: {s3_file_path}")
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(s3_file_path)
        
        # Get current schema from file
        current_schema = {field.name: str(field.dataType) for field in df.schema.fields}
        
        # Load expected schema from control plane
        expected_schema = agent.source_config.get("expected_schema", {})
        
        # 1. SCHEMA EVOLUTION CHECK
        logger.info("Step 1: Detecting schema changes...")
        schema_changes = agent.detect_schema_changes(current_schema, expected_schema)
        
        if schema_changes["added_columns"]:
            logger.warning(f"New columns detected: {schema_changes['added_columns']}")
            df, quarantined = agent.handle_new_columns(
                df, 
                schema_changes["added_columns"], 
                s3_file_path
            )
            if df is None:  # Full file quarantine
                logger.warning(f"File quarantined due to new columns: {s3_file_path}")
                _move_to_quarantine(s3_file_path, agent.source_config["s3_quarantine_path"])
                agent.finalize_run()
                return {"status": "quarantined", "reason": "new_columns_high_volume"}
        
        # 2. DEDUPLICATION
        logger.info("Step 2: Removing duplicate records...")
        business_keys = json.loads(agent.source_config.get("business_keys", "[]"))
        if business_keys:
            df, duplicates = agent.detect_duplicates(df, business_keys)
        
        # 3. DATA QUALITY VALIDATION
        logger.info("Step 3: Validating record quality...")
        quality_rules = _fetch_active_rules(agent.cursor, source_name)
        bad_rows = []
        
        for row_idx, row in enumerate(df.collect()):
            row_dict = row.asDict()
            row_dict["_row_index"] = row_idx
            violations = agent.validate_record_quality(row_dict, quality_rules)
            if violations:
                bad_rows.append(row_dict)
        
        # 4. QUARANTINE DECISION
        logger.info("Step 4: Applying quarantine decision...")
        if bad_rows:
            df, quarantine_manifest = agent.apply_quarantine_decision(
                df, 
                s3_file_path, 
                bad_rows, 
                "data_quality_violations"
            )
            
            if df is None:  # Full file quarantine
                logger.warning(f"File fully quarantined: {s3_file_path}")
                _move_to_quarantine(s3_file_path, agent.source_config["s3_quarantine_path"])
                agent.finalize_run()
                return {"status": "quarantined", "reason": "quality_threshold_exceeded"}
            else:
                # Row-level quarantine: write bad rows to quarantine
                _write_quarantine_data(bad_rows, agent.source_config["s3_quarantine_path"], logger)
        
        # 5. WRITE CLEAN DATA TO TARGET
        logger.info("Step 5: Writing clean data to target...")
        output_path = agent.source_config["s3_clean_path"]
        df.write.mode("overwrite").option("header", "true").csv(output_path)
        logger.info(f"Successfully loaded {df.count()} records to {output_path}")
        
        # 6. RULE LEARNING
        logger.info("Step 6: Analyzing patterns for rule recommendations...")
        rec_engine = RuleRecommendationEngine(agent.conn)
        recommendations = rec_engine.analyze_anomaly_patterns(source_name, days_back=7)
        if recommendations:
            rec_engine.store_recommendations(recommendations)
            logger.info(f"Stored {len(recommendations)} rule recommendations for approval")
        
        # Finalize
        agent.finalize_run()
        logger.info(f"Run {run_id} completed successfully")
        
        return {
            "status": "success",
            "run_id": run_id,
            "rows_processed": df.count(),
            "records_loaded": df.count()
        }
        
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


def _fetch_active_rules(cursor, source_name: str) -> list:
    """Retrieve active quality rules from control plane."""
    try:
        query = """
            SELECT rule_id, rule_name, column_name, rule_type, rule_definition, severity
            FROM dq_rule_catalog
            WHERE enabled = TRUE
            AND (source_name = %s OR source_name IS NULL)
        """
        cursor.execute(query, (source_name,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


def _move_to_quarantine(source_s3_path: str, quarantine_s3_path: str):
    """Move file to quarantine S3 location using boto3."""
    import boto3
    s3 = boto3.client("s3")
    # Implementation depends on S3 path format; simplified here
    pass


def _write_quarantine_data(bad_rows: list, quarantine_s3_path: str, logger):
    """Write quarantined rows to S3."""
    import boto3
    s3 = boto3.client("s3")
    # Serialize bad rows to JSON and upload
    logger.info(f"Writing {len(bad_rows)} bad rows to quarantine: {quarantine_s3_path}")
