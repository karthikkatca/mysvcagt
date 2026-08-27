from dataclasses import dataclass
from typing import List


@dataclass
class SourceConfig:
    source_name: str
    file_pattern: str
    s3_path: str
    business_keys: List[str]
    new_column_low_threshold_count: int
    new_column_high_threshold_count: int
    critical_columns: List[str]
    quarantine_s3_prefix: str
    clean_s3_prefix: str

