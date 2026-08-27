"""
AWS Glue Job Wrapper - S3 File-Based Version
Entry point for ELT Quality Agent execution using S3 CSV files for configuration.
NO REDSHIFT DEPENDENCY - All configuration stored in S3.
"""

import sys
import logging
import json
import boto3
import pandas as pd
from datetime import datetime
import uuid

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import DataFrame as SparkDataFrame
from schema_evolution_agent_s3 import SchemaEvolutionAgentS3


def setup_logging(job_name: str) -> logging.Logger:
    """Configure structured logging for Glue job."""
    logger = logging.getLogger(job_name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def move_to_s3(spark_df: SparkDataFrame, s3_path: str, logger: logging.Logger):
    """
    Write Spark DataFrame to S3 as CSV.
    
    Args:
        spark_df: Spark DataFrame
        s3_path: Target S3 path
        logger: Logger instance
    """
    try:
        logger.info(f"Writing data to: {s3_path}")
        spark_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(s3_path)
        logger.info(f"Successfully written to {s3_path}")
    except Exception as e:
        logger.error(f"Failed to write to S3: {e}")
        raise


def main():
    """
    AWS Glue job entry point for S3 file-based DQ agent.
    
    Expected Glue job parameters:
    --source_name: Source identifier (e.g., "SourceOne")
    --s3_inbound_file: Full S3 path to input file (e.g., "s3://bucket/inbound/file.csv")
    --s3_config_bucket: S3 bucket containing config files (e.g., "my-dq-config-bucket")
    --s3_config_prefix: Prefix for config files in bucket (e.g., "control/config")
    --s3_clean_prefix: Prefix for clean output files (e.g., "clean")
    --s3_quarantine_prefix: Prefix for quarantine files (e.g., "quarantine")
    --run_id: (Optional) Unique run identifier
    """
    
    # Parse Glue job arguments
    try:
        args = getResolvedOptions(sys.argv, [
            'JOB_NAME',
            'source_name',
            's3_inbound_file',
            's3_config_bucket',
            's3_config_prefix',
            's3_clean_prefix',
            's3_quarantine_prefix'
        ])
        
        # Optional run_id
        run_id = getResolvedOptions(sys.argv, ['run_id'])['run_id'] if 'run_id' in sys.argv else str(uuid.uuid4())
        
    except Exception as e:
        print(f"ERROR: Failed to parse job arguments: {e}")
        print("Required arguments: --source_name, --s3_inbound_file, --s3_config_bucket, --s3_config_prefix, --s3_clean_prefix, --s3_quarantine_prefix")
        sys.exit(1)
    
    job_name = args['JOB_NAME']
    source_name = args['source_name']
    s3_inbound_file = args['s3_inbound_file']
    s3_config_bucket = args['s3_config_bucket']
    s3_config_prefix = args['s3_config_prefix']
    s3_clean_prefix = args['s3_clean_prefix']
    s3_quarantine_prefix = args['s3_quarantine_prefix']
    
    logger = setup_logging(job_name)
    logger.info(f"Starting S3-based DQ Agent for source: {source_name}, run_id: {run_id}")
    logger.info(f"Config bucket: s3://{s3_config_bucket}/{s3_config_prefix}")
    logger.info(f"Input file: {s3_inbound_file}")
    
    # Initialize Spark/Glue
    sc = SparkContext.getOrCreate()
    glue_ctx = GlueContext(sc)
    spark = glue_ctx.spark_session
    job = Job(glue_ctx)
    job.init(job_name, args)
    
    try:
        # Initialize S3-based agent
        agent = SchemaEvolutionAgentS3(
            s3_config_bucket=s3_config_bucket,
            s3_config_prefix=s3_config_prefix,
            logger=logger
        )
        agent.run_id = run_id
        
        # Extract file name from S3 path
        file_name = s3_inbound_file.split('/')[-1]
        
        # Step 1: Load source configuration from S3 CSV
        logger.info("Step 1: Loading source configuration from S3...")
        agent.load_source_config(source_name)
        agent.source_config['current_file_name'] = file_name
        
        # Step 2: Load DQ rules from S3 CSV
        logger.info("Step 2: Loading DQ rules from S3...")
        agent.load_dq_rules(source_name)
        
        # Step 3: Read inbound file
        logger.info(f"Step 3: Reading inbound file: {s3_inbound_file}")
        spark_df = spark.read.option("header", "true").option("inferSchema", "true").csv(s3_inbound_file)
        
        # Convert to pandas for processing
        pandas_df = spark_df.toPandas()
        logger.info(f"Loaded {len(pandas_df)} records from inbound file")
        
        # Get current schema
        current_schema = {col: str(dtype) for col, dtype in pandas_df.dtypes.items()}
        expected_schema = agent.source_config.get("expected_schema", {})
        
        # Step 4: Schema validation
        logger.info("Step 4: Detecting schema changes...")
        schema_changes = agent.detect_schema_changes(current_schema, expected_schema)
        
        if schema_changes["added_columns"] or schema_changes["removed_columns"]:
            logger.warning(f"Schema changes detected: {schema_changes}")
            agent.write_anomaly_log(
                anomaly_type="schema_drift",
                severity="high",
                action_taken="logged",
                details=schema_changes
            )
        
        # Step 5: Deduplication
        logger.info("Step 5: Detecting duplicates...")
        business_keys = agent.source_config.get("business_keys", [])
        clean_df, duplicates_df = agent.detect_duplicates(pandas_df, business_keys)
        
        # Step 6: Data quality validation
        logger.info("Step 6: Applying data quality rules...")
        clean_df, bad_df = agent.apply_dq_validation(clean_df)
        
        # Step 7: Quarantine decision
        logger.info("Step 7: Making quarantine decision...")
        decision = agent.apply_quarantine_decision(clean_df, bad_df, duplicates_df)
        
        # Step 8: Write outputs to S3
        logger.info("Step 8: Writing output files to S3...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = file_name.rsplit('.', 1)[0]
        
        if decision['action'] == 'quarantine_file':
            # Full file quarantine - write everything to quarantine
            logger.warning("FULL FILE QUARANTINE - Writing entire file to quarantine folder")
            
            # Write original file to quarantine
            quarantine_path = f"s3://{s3_config_bucket}/{s3_quarantine_prefix}/{base_name}_QUARANTINED_{timestamp}.csv"
            quarantine_spark_df = spark.createDataFrame(pandas_df)
            move_to_s3(quarantine_spark_df, quarantine_path, logger)
            
            # Write duplicates if any
            if not duplicates_df.empty:
                dup_path = f"s3://{s3_config_bucket}/{s3_quarantine_prefix}/{base_name}_duplicates_{timestamp}.csv"
                dup_spark_df = spark.createDataFrame(duplicates_df)
                move_to_s3(dup_spark_df, dup_path, logger)
            
            # Write bad records if any
            if not bad_df.empty:
                bad_path = f"s3://{s3_config_bucket}/{s3_quarantine_prefix}/{base_name}_bad_records_{timestamp}.csv"
                bad_spark_df = spark.createDataFrame(bad_df)
                move_to_s3(bad_spark_df, bad_path, logger)
            
            logger.warning(f"File quarantined: {decision['bad_percent']:.2f}% bad records exceeds {decision['threshold']}% threshold")
            
        else:
            # Row-level quarantine - write clean records to clean folder
            logger.info("ROW-LEVEL QUARANTINE - Writing clean records to clean folder")
            
            if not clean_df.empty:
                clean_path = f"s3://{s3_config_bucket}/{s3_clean_prefix}/{base_name}_clean_{timestamp}.csv"
                clean_spark_df = spark.createDataFrame(clean_df)
                move_to_s3(clean_spark_df, clean_path, logger)
                logger.info(f"Written {len(clean_df)} clean records")
            else:
                logger.warning("No clean records to write")
            
            # Write quarantine files
            if not duplicates_df.empty:
                dup_path = f"s3://{s3_config_bucket}/{s3_quarantine_prefix}/{base_name}_duplicates_{timestamp}.csv"
                dup_spark_df = spark.createDataFrame(duplicates_df)
                move_to_s3(dup_spark_df, dup_path, logger)
                logger.info(f"Written {len(duplicates_df)} duplicate records")
            
            if not bad_df.empty:
                bad_path = f"s3://{s3_config_bucket}/{s3_quarantine_prefix}/{base_name}_bad_records_{timestamp}.csv"
                bad_spark_df = spark.createDataFrame(bad_df)
                move_to_s3(bad_spark_df, bad_path, logger)
                logger.info(f"Written {len(bad_df)} bad records")
        
        # Step 9: Write logs and manifest to S3
        logger.info("Step 9: Writing logs and quarantine manifest to S3...")
        agent.finalize_run()
        
        # Job summary
        logger.info("=" * 80)
        logger.info("JOB SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Source: {source_name}")
        logger.info(f"Input file: {s3_inbound_file}")
        logger.info(f"Total records: {len(pandas_df)}")
        logger.info(f"Clean records: {len(clean_df)}")
        logger.info(f"Duplicate records: {len(duplicates_df)}")
        logger.info(f"Bad records (DQ violations): {len(bad_df)}")
        logger.info(f"Quarantine action: {decision['action']}")
        logger.info(f"Bad record %: {decision['bad_percent']:.2f}%")
        logger.info(f"Anomalies logged: {len(agent.anomalies)}")
        logger.info("=" * 80)
        
        job.commit()
        logger.info("Job completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'run_id': run_id,
                'source_name': source_name,
                'total_records': len(pandas_df),
                'clean_records': len(clean_df),
                'quarantine_action': decision['action'],
                'bad_percent': decision['bad_percent']
            })
        }
        
    except Exception as e:
        logger.error(f"Job failed with error: {e}", exc_info=True)
        raise
    

if __name__ == "__main__":
    main()
