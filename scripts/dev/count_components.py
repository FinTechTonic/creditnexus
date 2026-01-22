#!/usr/bin/env python3
"""
Script to count components in CreditNexus application.
Counts prompts, agents, policies, tools, and datapoints.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def count_prompts():
    """Count prompt templates and functions."""
    prompt_dir = Path("app/prompts")
    prompt_files = list(prompt_dir.rglob("*.py"))
    
    prompt_count = 0
    prompt_functions = 0
    
    for file_path in prompt_files:
        if file_path.name == "__init__.py":
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Count ChatPromptTemplate instances
            prompt_count += len(re.findall(r'ChatPromptTemplate\.from_messages|PROMPT\s*=', content))
            
            # Count prompt functions
            prompt_functions += len(re.findall(r'def.*prompt|PROMPT.*=', content, re.IGNORECASE))
    
    return {
        "files": len(prompt_files),
        "templates": prompt_count,
        "functions": prompt_functions
    }

def count_agents():
    """Count agent files and classes."""
    agent_dir = Path("app/agents")
    agent_files = [f for f in agent_dir.glob("*.py") if f.name != "__init__.py"]
    
    agent_classes = 0
    agent_functions = 0
    
    for file_path in agent_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            agent_classes += len(re.findall(r'^class\s+\w+.*:', content, re.MULTILINE))
            agent_functions += len(re.findall(r'^def\s+\w+.*:', content, re.MULTILINE))
    
    return {
        "files": len(agent_files),
        "classes": agent_classes,
        "functions": agent_functions
    }

def count_policies():
    """Count policy YAML files and rules."""
    policy_dir = Path("app/policies")
    policy_files = list(policy_dir.rglob("*.yaml"))
    
    total_rules = 0
    
    for file_path in policy_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Count rules (usually start with - name:)
            total_rules += len(re.findall(r'^\s*-\s+name:', content, re.MULTILINE))
    
    return {
        "files": len(policy_files),
        "rules": total_rules
    }

def count_tools():
    """Count tools (services, utils, chains)."""
    services_dir = Path("app/services")
    utils_dir = Path("app/utils")
    chains_dir = Path("app/chains")
    
    service_files = [f for f in services_dir.glob("*.py") if f.name != "__init__.py"]
    util_files = [f for f in utils_dir.glob("*.py") if f.name != "__init__.py"]
    chain_files = [f for f in chains_dir.glob("*.py") if f.name != "__init__.py"]
    
    service_classes = 0
    service_functions = 0
    util_functions = 0
    chain_classes = 0
    chain_functions = 0
    
    for file_path in service_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            service_classes += len(re.findall(r'^class\s+\w+.*:', content, re.MULTILINE))
            service_functions += len(re.findall(r'^def\s+\w+.*:', content, re.MULTILINE))
    
    for file_path in util_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            util_functions += len(re.findall(r'^def\s+\w+.*:', content, re.MULTILINE))
    
    for file_path in chain_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            chain_classes += len(re.findall(r'^class\s+\w+.*:', content, re.MULTILINE))
            chain_functions += len(re.findall(r'^def\s+\w+.*:', content, re.MULTILINE))
    
    return {
        "services": {
            "files": len(service_files),
            "classes": service_classes,
            "functions": service_functions
        },
        "utils": {
            "files": len(util_files),
            "functions": util_functions
        },
        "chains": {
            "files": len(chain_files),
            "classes": chain_classes,
            "functions": chain_functions
        }
    }

def count_datapoints():
    """Count datapoints (models, database tables, API endpoints)."""
    models_dir = Path("app/models")
    db_models_file = Path("app/db/models.py")
    api_routes_file = Path("app/api/routes.py")
    
    model_files = [f for f in models_dir.glob("*.py") if f.name != "__init__.py"]
    
    pydantic_models = 0
    db_tables = 0
    api_endpoints = 0
    
    # Count Pydantic models
    for file_path in model_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            pydantic_models += len(re.findall(r'^class\s+\w+.*BaseModel', content, re.MULTILINE))
    
    # Count database tables
    if db_models_file.exists():
        with open(db_models_file, 'r', encoding='utf-8') as f:
            content = f.read()
            db_tables += len(re.findall(r'class\s+\w+.*\(Base\)', content))
    
    # Count API endpoints
    if api_routes_file.exists():
        with open(api_routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            api_endpoints += len(re.findall(r'@router\.(get|post|put|patch|delete)', content))
    
    return {
        "pydantic_models": pydantic_models,
        "database_tables": db_tables,
        "api_endpoints": api_endpoints,
        "model_files": len(model_files)
    }

def main():
    """Main function to count all components."""
    print("CreditNexus Component Analysis")
    print("=" * 50)
    
    prompts = count_prompts()
    print(f"\nPROMPTS:")
    print(f"  Files: {prompts['files']}")
    print(f"  Templates: {prompts['templates']}")
    print(f"  Functions: {prompts['functions']}")
    
    agents = count_agents()
    print(f"\nAGENTS:")
    print(f"  Files: {agents['files']}")
    print(f"  Classes: {agents['classes']}")
    print(f"  Functions: {agents['functions']}")
    
    policies = count_policies()
    print(f"\nPOLICIES:")
    print(f"  Files: {policies['files']}")
    print(f"  Rules: {policies['rules']}")
    
    tools = count_tools()
    print(f"\nTOOLS:")
    print(f"  Services: {tools['services']['files']} files, {tools['services']['classes']} classes, {tools['services']['functions']} functions")
    print(f"  Utils: {tools['utils']['files']} files, {tools['utils']['functions']} functions")
    print(f"  Chains: {tools['chains']['files']} files, {tools['chains']['classes']} classes, {tools['chains']['functions']} functions")
    print(f"  Total Tools: {tools['services']['files'] + tools['utils']['files'] + tools['chains']['files']} files")
    
    datapoints = count_datapoints()
    print(f"\nDATAPOINTS:")
    print(f"  Pydantic Models: {datapoints['pydantic_models']}")
    print(f"  Database Tables: {datapoints['database_tables']}")
    print(f"  API Endpoints: {datapoints['api_endpoints']}")
    print(f"  Model Files: {datapoints['model_files']}")
    
    # Summary
    print(f"\n{'=' * 50}")
    print("SUMMARY:")
    print(f"  Total Prompts: ~{prompts['templates']} templates")
    print(f"  Total Agents: {agents['files']} files")
    print(f"  Total Policies: {policies['files']} files, {policies['rules']} rules")
    print(f"  Total Tools: {tools['services']['files'] + tools['utils']['files'] + tools['chains']['files']} files")
    print(f"  Total Datapoints: {datapoints['pydantic_models']} models, {datapoints['database_tables']} tables, {datapoints['api_endpoints']} endpoints")
    
    return {
        "prompts": prompts,
        "agents": agents,
        "policies": policies,
        "tools": tools,
        "datapoints": datapoints
    }

if __name__ == "__main__":
    results = main()
