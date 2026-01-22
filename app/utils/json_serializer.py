"""
JSON serialization utilities for CDM data.

Handles serialization of Pydantic models containing Decimal, datetime, UUID, and other
non-JSON-serializable types for database storage (JSONB columns).
"""

import json
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict
from enum import Enum


def serialize_cdm_data(data: Any) -> Dict[str, Any]:
    """
    Serialize CDM data to JSON-safe dictionary.
    
    Converts:
    - Decimal -> float
    - datetime -> ISO format string
    - date -> ISO format string
    - UUID -> string
    - Enum -> value
    - Pydantic models -> dict (recursively)
    
    Args:
        data: CDM data (Pydantic model, dict, or any serializable object)
        
    Returns:
        JSON-serializable dictionary
    """
    if isinstance(data, dict):
        return {key: serialize_cdm_data(value) for key, value in data.items()}
    elif isinstance(data, (list, tuple)):
        return [serialize_cdm_data(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    elif isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, Enum):
        return data.value
    elif hasattr(data, 'model_dump'):
        # Pydantic v2
        return serialize_cdm_data(data.model_dump())
    elif hasattr(data, 'dict'):
        # Pydantic v1
        return serialize_cdm_data(data.dict())
    elif hasattr(data, '__dict__'):
        # Regular object with __dict__
        return serialize_cdm_data(data.__dict__)
    else:
        # Try to serialize - if it fails, convert to string
        try:
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            return str(data)


def json_dumps_cdm(data: Any) -> str:
    """
    Serialize CDM data to JSON string.
    
    Args:
        data: CDM data to serialize
        
    Returns:
        JSON string
    """
    serialized = serialize_cdm_data(data)
    return json.dumps(serialized, default=str)




