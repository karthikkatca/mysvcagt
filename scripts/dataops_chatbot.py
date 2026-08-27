"""
DataOps Chatbot - Natural language interface to ELT quality data.
Uses LLM-to-SQL pattern for safe, controlled database queries.
"""

import os
import json
import logging
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

# Mock Bedrock client for LLM inference
class BedrockLLMClient:
    """Interface to Amazon Bedrock for LLM inference."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        self.model_id = model_id
        # In real implementation, use boto3 to invoke Bedrock
    
    def generate_sql(self, user_query: str, schema_context: str) -> str:
        """
        Generate SQL from natural language query using LLM.
        
        Args:
            user_query: Natural language question
            schema_context: Available tables and views
            
        Returns:
            Generated SQL query (safety-checked)
        """
        prompt = f"""
You are a SQL expert assistant for data quality analytics. 
Your role is to convert user questions into precise, safe SQL queries.

Available tables and views:
{schema_context}

User question: {user_query}

Generate ONLY a SELECT query. No INSERT, UPDATE, DELETE, or DROP statements.
Respond with SQL only, no explanation.
"""
        # In real implementation, call Bedrock API
        # For now, return example queries
        if "quarantine" in user_query.lower():
            return "SELECT * FROM vw_quarantine_summary LIMIT 10;"
        elif "anomaly" in user_query.lower() or "drift" in user_query.lower():
            return "SELECT * FROM dq_anomaly_log LIMIT 20 ORDER BY event_timestamp DESC;"
        return "SELECT * FROM vw_file_health LIMIT 10;"


class DataOpsChat:
    """Chatbot interface for data quality questions."""
    
    def __init__(self, db_config: Dict, logger: logging.Logger):
        self.db_config = db_config
        self.logger = logger
        self.conn = None
        self.cursor = None
        self.llm_client = BedrockLLMClient()
    
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
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
    
    def get_schema_context(self) -> str:
        """Fetch available tables and views for LLM context."""
        context = """
-- Analytics Views (Available for queries)
- vw_file_health: source_name, file_name, latest_run_id, last_processed, critical_anomalies, duplicate_count, schema_drift_count
- vw_quarantine_summary: source_name, quarantine_date, files_quarantined, total_rows_quarantined, avg_quarantine_percent
- vw_schema_drift: source_name, drift_date, drift_events, distinct_columns_affected, columns_involved
- vw_rule_recommendation_status: recommendation_status, count, avg_confidence

-- Detailed Tables (Use for drill-downs)
- dq_anomaly_log: event_timestamp, source_name, file_name, anomaly_type, severity, action_taken, resolved
- dq_quarantine_manifest: source_name, quarantine_level, quarantine_reason, quarantined_row_count
- dq_lineage_audit: run_id, source_name, processing_duration_seconds, step_status
"""
        return context
    
    def process_query(self, user_query: str, user_id: str = None) -> Dict:
        """
        Process a natural language query and return results.
        
        Args:
            user_query: User's natural language question
            user_id: Optional user identifier for audit
            
        Returns:
            Dict with results, explanation, and confidence
        """
        try:
            # Log query
            self._audit_query(user_query, user_id, "pending")
            
            # Get schema context
            schema_context = self.get_schema_context()
            
            # Generate SQL from NL
            sql = self.llm_client.generate_sql(user_query, schema_context)
            self.logger.info(f"Generated SQL: {sql}")
            
            # Validate SQL (safety checks)
            if not self._is_safe_sql(sql):
                return {
                    "status": "error",
                    "message": "Query validation failed - potentially unsafe operation",
                    "confidence": 0.0
                }
            
            # Execute query
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
            result_count = len(results)
            
            # Format response
            response = {
                "status": "success",
                "query_text": user_query,
                "generated_sql": sql,
                "result_count": result_count,
                "results": results if result_count <= 50 else results[:50],
                "confidence": 0.85
            }
            
            # Log success
            self._audit_query(user_query, user_id, "success")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            self._audit_query(user_query, user_id, "failed", str(e))
            return {
                "status": "error",
                "message": str(e),
                "confidence": 0.0
            }
    
    def common_queries_menu(self) -> List[Dict]:
        """Provide pre-built query suggestions for users."""
        return [
            {
                "description": "Show file health status for all sources",
                "sql": "SELECT * FROM vw_file_health ORDER BY last_processed DESC;",
                "query_type": "file_status"
            },
            {
                "description": "Show quarantine trends over past 7 days",
                "sql": "SELECT * FROM vw_quarantine_summary WHERE quarantine_date >= CURRENT_DATE - 7;",
                "query_type": "quarantine_stats"
            },
            {
                "description": "Show schema drift events by source",
                "sql": "SELECT * FROM vw_schema_drift WHERE drift_date >= CURRENT_DATE - 30;",
                "query_type": "schema_drift"
            },
            {
                "description": "Show pending rule recommendations",
                "sql": "SELECT * FROM vw_rule_recommendation_status WHERE recommendation_status = 'pending';",
                "query_type": "rule_status"
            },
            {
                "description": "Show critical anomalies in the last 24 hours",
                "sql": """
                    SELECT source_name, file_name, anomaly_type, COUNT(*) as count
                    FROM dq_anomaly_log
                    WHERE severity = 'critical' AND event_timestamp >= NOW() - INTERVAL '24 hours'
                    GROUP BY source_name, file_name, anomaly_type
                    ORDER BY count DESC;
                """,
                "query_type": "critical_anomalies"
            }
        ]
    
    def _is_safe_sql(self, sql: str) -> bool:
        """Validate SQL for security - reject INSERT, UPDATE, DELETE, DROP, etc."""
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        sql_upper = sql.upper().strip()
        
        for keyword in dangerous_keywords:
            if sql_upper.startswith(keyword):
                return False
        
        if ";" in sql:
            # Allow semicolon only at end
            if sql.count(";") > 1 or not sql.rstrip().endswith(";"):
                return False
        
        return True
    
    def _audit_query(self, user_query: str, user_id: str, status: str, error_msg: str = None):
        """Log query for audit trail."""
        try:
            audit_query = """
                INSERT INTO chatbot_query_audit
                (user_id, user_query, query_type, was_successful, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            is_successful = status == "success"
            self.cursor.execute(
                audit_query,
                (user_id or "anonymous", user_query[:500], "nlu_query", is_successful, error_msg)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"Failed to audit query: {e}")
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


# Flask API endpoint example
from flask import Flask, request, jsonify

def create_chatbot_api():
    """Create Flask API for chatbot endpoint."""
    app = Flask(__name__)
    
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    logger = logging.getLogger("DataOpsChat")
    chat = DataOpsChat(db_config, logger)
    chat.connect()
    
    @app.route("/chat", methods=["POST"])
    def handle_query():
        """POST /chat endpoint for natural language queries."""
        try:
            payload = request.get_json()
            user_query = payload.get("query")
            user_id = payload.get("user_id")
            
            result = chat.process_query(user_query, user_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    @app.route("/suggestions", methods=["GET"])
    def get_suggestions():
        """GET /suggestions endpoint for query suggestions."""
        suggestions = chat.common_queries_menu()
        return jsonify({"suggestions": suggestions})
    
    return app
