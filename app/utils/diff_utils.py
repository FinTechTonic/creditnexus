"""Utility functions for generating and applying diffs between document versions."""

import logging
from typing import Dict, Any, List, Optional
from deepdiff import DeepDiff

logger = logging.getLogger(__name__)


def generate_json_diff(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a structured diff between two JSON objects.
    
    Args:
        old_data: The original data (old version)
        new_data: The modified data (new version)
        
    Returns:
        Dictionary containing diff information with:
        - added: Fields added in new_data
        - removed: Fields removed from old_data
        - changed: Fields that changed
        - unchanged: Fields that remained the same
    """
    try:
        diff = DeepDiff(old_data, new_data, ignore_order=False, verbose_level=2)
        
        result = {
            "added": [],
            "removed": [],
            "changed": [],
            "unchanged": []
        }
        
        # Process added items
        if 'dictionary_item_added' in diff:
            for item in diff['dictionary_item_added']:
                path = item.path(output_format='list')
                result["added"].append({
                    "path": ".".join(str(p) for p in path),
                    "value": item.t2 if hasattr(item, 't2') else None
                })
        
        # Process removed items
        if 'dictionary_item_removed' in diff:
            for item in diff['dictionary_item_removed']:
                path = item.path(output_format='list')
                result["removed"].append({
                    "path": ".".join(str(p) for p in path),
                    "value": item.t1 if hasattr(item, 't1') else None
                })
        
        # Process changed items
        if 'values_changed' in diff:
            for item in diff['values_changed']:
                path = item.path(output_format='list')
                result["changed"].append({
                    "path": ".".join(str(p) for p in path),
                    "old_value": item.t1 if hasattr(item, 't1') else None,
                    "new_value": item.t2 if hasattr(item, 't2') else None
                })
        
        # Process iterable items (for arrays)
        if 'iterable_item_added' in diff:
            for item in diff['iterable_item_added']:
                path = item.path(output_format='list')
                result["added"].append({
                    "path": ".".join(str(p) for p in path),
                    "value": item.t2 if hasattr(item, 't2') else None
                })
        
        if 'iterable_item_removed' in diff:
            for item in diff['iterable_item_removed']:
                path = item.path(output_format='list')
                result["removed"].append({
                    "path": ".".join(str(p) for p in path),
                    "value": item.t1 if hasattr(item, 't1') else None
                })
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating diff: {e}", exc_info=True)
        return {
            "added": [],
            "removed": [],
            "changed": [],
            "unchanged": [],
            "error": str(e)
        }


def apply_diff(base_data: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a diff to base data to reconstruct the new version.
    
    Args:
        base_data: The base data to apply changes to
        diff: The diff dictionary from generate_json_diff
        
    Returns:
        New data with diff applied
    """
    import copy
    
    result = copy.deepcopy(base_data)
    
    try:
        # Apply additions
        for item in diff.get("added", []):
            path = item["path"].split(".")
            _set_nested_value(result, path, item["value"])
        
        # Apply changes
        for item in diff.get("changed", []):
            path = item["path"].split(".")
            _set_nested_value(result, path, item["new_value"])
        
        # Apply removals
        for item in diff.get("removed", []):
            path = item["path"].split(".")
            _remove_nested_value(result, path)
        
        return result
        
    except Exception as e:
        logger.error(f"Error applying diff: {e}", exc_info=True)
        raise


def _set_nested_value(obj: Dict[str, Any], path: List[str], value: Any) -> None:
    """Set a nested value in a dictionary using a path."""
    for key in path[:-1]:
        if key not in obj:
            obj[key] = {}
        obj = obj[key]
    obj[path[-1]] = value


def _remove_nested_value(obj: Dict[str, Any], path: List[str]) -> None:
    """Remove a nested value from a dictionary using a path."""
    for key in path[:-1]:
        if key not in obj:
            return
        obj = obj[key]
    if path[-1] in obj:
        del obj[path[-1]]


def format_diff_for_display(diff: Dict[str, Any]) -> Dict[str, Any]:
    """Format diff for UI display with human-readable changes.
    
    Args:
        diff: The diff dictionary from generate_json_diff
        
    Returns:
        Formatted diff with display-friendly strings
    """
    formatted = {
        "added": [],
        "removed": [],
        "changed": [],
        "summary": {
            "total_changes": 0,
            "added_count": 0,
            "removed_count": 0,
            "changed_count": 0
        }
    }
    
    # Format added items
    for item in diff.get("added", []):
        formatted["added"].append({
            "path": item["path"],
            "value": _format_value(item.get("value")),
            "display": f"Added: {item['path']} = {_format_value(item.get('value'))}"
        })
    
    # Format removed items
    for item in diff.get("removed", []):
        formatted["removed"].append({
            "path": item["path"],
            "value": _format_value(item.get("value")),
            "display": f"Removed: {item['path']} = {_format_value(item.get('value'))}"
        })
    
    # Format changed items
    for item in diff.get("changed", []):
        formatted["changed"].append({
            "path": item["path"],
            "old_value": _format_value(item.get("old_value")),
            "new_value": _format_value(item.get("new_value")),
            "display": f"Changed: {item['path']} ({_format_value(item.get('old_value'))} → {_format_value(item.get('new_value'))})"
        })
    
    # Calculate summary
    formatted["summary"]["added_count"] = len(formatted["added"])
    formatted["summary"]["removed_count"] = len(formatted["removed"])
    formatted["summary"]["changed_count"] = len(formatted["changed"])
    formatted["summary"]["total_changes"] = (
        formatted["summary"]["added_count"] +
        formatted["summary"]["removed_count"] +
        formatted["summary"]["changed_count"]
    )
    
    return formatted


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "{...}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    if isinstance(value, str) and len(value) > 50:
        return value[:50] + "..."
    return str(value)
