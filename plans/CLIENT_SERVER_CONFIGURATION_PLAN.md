# Client-Server Configuration Management Plan
## Complete Configuration System with AI-Assisted UI

**Status**: Complete Implementation Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 8-10 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan provides a **complete client-server configuration management system** that:
- Inventories and categorizes all configuration options (server and client)
- Ensures client-server configuration compatibility
- Provides setup/configure scripts for distributed clients
- Implements **admin-only** AI-assisted configuration UI using "add clause" / "remove clause" patterns
- Implements **admin-only** AI-assisted policy decision editing
- Supports **organization-specific policies** based on default policies
- Supports commission-based trading (users execute trades, CreditNexus takes commission)
- Validates configuration before client-server communication

---

## Current State Analysis

### ✅ Server Configuration

**Location**: `app/core/config.py`

**Categories**:
1. **LLM Provider Configuration** (Lines 47-106)
   - LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE
   - vLLM, HuggingFace, OpenAI settings
   - Embeddings configuration

2. **Policy Engine Configuration** (Lines 108-115)
   - POLICY_ENABLED, POLICY_RULES_DIR, POLICY_ENGINE_VENDOR

3. **External Service APIs** (Lines 123-244)
   - DigiSigner, Companies House, x402 Payment
   - Polygon, Alpha Vantage, Tavily, Tickertick
   - Twilio, SentinelHub

4. **Blockchain Configuration** (Lines 153-188)
   - Securitization contracts, USDC token, auto-deployment

5. **Payment & Fees** (Lines 190-206)
   - Notarization fees, commission settings

6. **Database Configuration** (Lines 355-372)
   - DATABASE_URL, SSL settings, auto-cert generation

7. **Security Configuration** (Lines 384-401)
   - JWT, encryption, CORS, rate limiting

8. **Feature Flags** (Various)
   - DEMO_DATA_ENABLED, TWILIO_ENABLED, X402_ENABLED, etc.

### ❌ Client Configuration

**Current State**:
- No structured configuration system
- Uses localStorage/sessionStorage for UI state only
- No client-server config sync
- No configuration UI
- No setup scripts

**Missing**:
- Client configuration model
- Configuration sync with server
- Configuration validation
- Setup/configure scripts
- Configuration UI

### ✅ AI Patterns Available

**Add Clause Pattern**:
- `app/chains/cdm_add_chain.py` - AI-assisted addition
- Uses structured LLM output
- Multimodal context support

**Remove Clause Pattern**:
- `app/chains/cdm_remove_chain.py` - AI-assisted removal
- Safety evaluation before removal
- Alternative action suggestions

**Existing Config UI**:
- `client/src/apps/verification-config/VerificationFileConfigEditor.tsx` - YAML editor

### ⚠️ Trading & Commission

**Current State**:
- Trades executed by users themselves (`/api/trades/execute`)
- Commission system planned but not fully implemented
- No "trade on behalf" functionality (by design - users execute, CreditNexus takes commission)

---

## Project 1: Configuration Inventory & Categorization

### Activity 1.1: Server Configuration Schema

**File**: `app/core/config_schema.py` (NEW)

#### Task 1.1.1: Create Configuration Schema
**Lines**: 1-500

**Subtasks**:
1. **Line 1-200**: Schema definitions
   ```python
   from enum import Enum
   from typing import Optional, List, Dict, Any, Literal
   from pydantic import BaseModel, Field
   
   class ConfigCategory(str, Enum):
       """Configuration categories."""
       LLM = "llm"
       POLICY = "policy"
       EXTERNAL_API = "external_api"
       BLOCKCHAIN = "blockchain"
       PAYMENT = "payment"
       DATABASE = "database"
       SECURITY = "security"
       FEATURE_FLAG = "feature_flag"
       UI = "ui"
       TRADING = "trading"
       COMMISSION = "commission"
   
   class ConfigScope(str, Enum):
       """Configuration scope."""
       SERVER_ONLY = "server_only"  # Only on server
       CLIENT_ONLY = "client_only"  # Only on client
       SHARED = "shared"  # Both client and server
       SYNCED = "synced"  # Synced from server to client
   
   class ConfigFieldType(str, Enum):
       """Configuration field types."""
       STRING = "string"
       INTEGER = "integer"
       FLOAT = "float"
       BOOLEAN = "boolean"
       ENUM = "enum"
       SECRET = "secret"  # Encrypted/secret value
       PATH = "path"
       URL = "url"
       JSON = "json"
       LIST = "list"
   
   class ConfigFieldMetadata(BaseModel):
       """Metadata for a configuration field."""
       name: str
       category: ConfigCategory
       scope: ConfigScope
       field_type: ConfigFieldType
       description: str
       default_value: Optional[Any] = None
       required: bool = False
       server_key: str  # Environment variable name
       client_key: Optional[str] = None  # Client storage key
       validation_rules: Optional[Dict[str, Any]] = None
       enum_values: Optional[List[str]] = None
       min_value: Optional[float] = None
       max_value: Optional[float] = None
       allowed_pattern: Optional[str] = None
       depends_on: Optional[List[str]] = None  # Other config fields this depends on
       affects: Optional[List[str]] = None  # Features this config affects
       ai_editable: bool = True  # Can be edited via AI
       ui_component: Optional[str] = None  # "select", "input", "checkbox", "textarea", "ai_assist"
   
   class ConfigurationSchema(BaseModel):
       """Complete configuration schema."""
       version: str = "1.0"
       fields: List[ConfigFieldMetadata]
       
       def get_by_category(self, category: ConfigCategory) -> List[ConfigFieldMetadata]:
           """Get all fields in a category."""
           return [f for f in self.fields if f.category == category]
       
       def get_by_scope(self, scope: ConfigScope) -> List[ConfigFieldMetadata]:
           """Get all fields in a scope."""
           return [f for f in self.fields if f.scope == scope]
       
       def get_client_config(self) -> List[ConfigFieldMetadata]:
           """Get all client-visible configuration fields."""
           return [
               f for f in self.fields
               if f.scope in [ConfigScope.CLIENT_ONLY, ConfigScope.SHARED, ConfigScope.SYNCED]
           ]
   ```

2. **Line 201-500**: Generate schema from Settings
   ```python
   def generate_config_schema() -> ConfigurationSchema:
       """Generate configuration schema from Settings class."""
       from app.core.config import Settings
       
       fields = []
       
       # LLM Configuration
       fields.append(ConfigFieldMetadata(
           name="LLM Provider",
           category=ConfigCategory.LLM,
           scope=ConfigScope.SHARED,
           field_type=ConfigFieldType.ENUM,
           description="LLM provider: OpenAI, vLLM, or HuggingFace",
           default_value="openai",
           required=True,
           server_key="LLM_PROVIDER",
           client_key="llm.provider",
           enum_values=["openai", "vllm", "huggingface"],
           ui_component="select",
           affects=["document_extraction", "quantitative_analysis", "chatbot"]
       ))
       
       fields.append(ConfigFieldMetadata(
           name="LLM Model",
           category=ConfigCategory.LLM,
           scope=ConfigScope.SHARED,
           field_type=ConfigFieldType.STRING,
           description="LLM model identifier",
           default_value="gpt-4o",
           required=True,
           server_key="LLM_MODEL",
           client_key="llm.model",
           ui_component="input",
           depends_on=["LLM_PROVIDER"]
       ))
       
       fields.append(ConfigFieldMetadata(
           name="LLM Temperature",
           category=ConfigCategory.LLM,
           scope=ConfigScope.SHARED,
           field_type=ConfigFieldType.FLOAT,
           description="Temperature for generation (0.0 = deterministic, 1.0 = creative)",
           default_value=0.0,
           required=False,
           server_key="LLM_TEMPERATURE",
           client_key="llm.temperature",
           min_value=0.0,
           max_value=1.0,
           ui_component="input"
       ))
       
       # OpenAI API Key
       fields.append(ConfigFieldMetadata(
           name="OpenAI API Key",
           category=ConfigCategory.EXTERNAL_API,
           scope=ConfigScope.SERVER_ONLY,
           field_type=ConfigFieldType.SECRET,
           description="OpenAI API key (required for all providers)",
           required=True,
           server_key="OPENAI_API_KEY",
           ui_component="input",
           ai_editable=False  # Secrets should not be AI-editable
       ))
       
       # Commission Configuration
       fields.append(ConfigFieldMetadata(
           name="Commission Enabled",
           category=ConfigCategory.COMMISSION,
           scope=ConfigScope.SHARED,
           field_type=ConfigFieldType.BOOLEAN,
           description="Enable commission calculation for trades",
           default_value=True,
           required=False,
           server_key="COMMISSION_ENABLED",
           client_key="commission.enabled",
           ui_component="checkbox",
           affects=["trade_execution", "market_creation"]
       ))
       
       fields.append(ConfigFieldMetadata(
           name="Default Commission Rate",
           category=ConfigCategory.COMMISSION,
           scope=ConfigScope.SHARED,
           field_type=ConfigFieldType.FLOAT,
           description="Default commission rate as percentage (e.g., 0.5 = 0.5%)",
           default_value=0.5,
           required=False,
           server_key="DEFAULT_COMMISSION_RATE",
           client_key="commission.default_rate",
           min_value=0.0,
           max_value=100.0,
           ui_component="input",
           depends_on=["COMMISSION_ENABLED"]
       ))
       
       # Trading Configuration
       fields.append(ConfigFieldMetadata(
           name="Trading Enabled",
           category=ConfigCategory.TRADING,
           scope=ConfigScope.SHARED,
           field_type=ConfigFieldType.BOOLEAN,
           description="Enable trading functionality",
           default_value=True,
           required=False,
           server_key="TRADING_ENABLED",
           client_key="trading.enabled",
           ui_component="checkbox",
           affects=["trade_blotter", "portfolio_dashboard"]
       ))
       
       fields.append(ConfigFieldMetadata(
           name="Allow Trade on Behalf",
           category=ConfigCategory.TRADING,
           scope=ConfigScope.SERVER_ONLY,
           field_type=ConfigFieldType.BOOLEAN,
           description="Allow CreditNexus to execute trades on behalf of users (DISABLED - users execute, CreditNexus takes commission)",
           default_value=False,
           required=False,
           server_key="ALLOW_TRADE_ON_BEHALF",
           ui_component="checkbox",
           affects=["trade_execution"]
       ))
       
       # Add all other configuration fields...
       
       return ConfigurationSchema(fields=fields)
   ```

---

## Project 2: Client Configuration System

### Activity 2.1: Client Configuration Models

**File**: `client/src/types/config.ts` (NEW)

#### Task 2.1.1: Create Client Config Types
**Lines**: 1-300

**Subtasks**:
1. **Line 1-200**: TypeScript types
   ```typescript
   export enum ConfigCategory {
     LLM = "llm",
     POLICY = "policy",
     EXTERNAL_API = "external_api",
     BLOCKCHAIN = "blockchain",
     PAYMENT = "payment",
     DATABASE = "database",
     SECURITY = "security",
     FEATURE_FLAG = "feature_flag",
     UI = "ui",
     TRADING = "trading",
     COMMISSION = "commission"
   }
   
   export enum ConfigScope {
     SERVER_ONLY = "server_only",
     CLIENT_ONLY = "client_only",
     SHARED = "shared",
     SYNCED = "synced"
   }
   
   export enum ConfigFieldType {
     STRING = "string",
     INTEGER = "integer",
     FLOAT = "float",
     BOOLEAN = "boolean",
     ENUM = "enum",
     SECRET = "secret",
     PATH = "path",
     URL = "url",
     JSON = "json",
     LIST = "list"
   }
   
   export interface ConfigFieldMetadata {
     name: string;
     category: ConfigCategory;
     scope: ConfigScope;
     field_type: ConfigFieldType;
     description: string;
     default_value?: any;
     required: boolean;
     server_key: string;
     client_key?: string;
     validation_rules?: Record<string, any>;
     enum_values?: string[];
     min_value?: number;
     max_value?: number;
     allowed_pattern?: string;
     depends_on?: string[];
     affects?: string[];
     ai_editable: boolean;
     ui_component?: "select" | "input" | "checkbox" | "textarea" | "ai_assist";
   }
   
   export interface ConfigurationSchema {
     version: string;
     fields: ConfigFieldMetadata[];
   }
   
   export interface ClientConfiguration {
     // LLM Configuration
     llm: {
       provider: string;
       model: string;
       temperature: number;
     };
     
     // Commission Configuration
     commission: {
       enabled: boolean;
       default_rate: number;
     };
     
     // Trading Configuration
     trading: {
       enabled: boolean;
     };
     
     // UI Configuration
     ui: {
       theme: "light" | "dark" | "system";
       sidebar_collapsed: boolean;
     };
     
     // Feature Flags
     features: {
       [key: string]: boolean;
     };
   }
   
   export interface ConfigSyncStatus {
     last_synced: string | null;
     server_version: string;
     client_version: string;
     conflicts: ConfigConflict[];
   }
   
   export interface ConfigConflict {
     field: string;
     server_value: any;
     client_value: any;
     resolution: "server" | "client" | "manual";
   }
   ```

### Activity 2.2: Client Configuration Service

**File**: `client/src/services/configService.ts` (NEW)

#### Task 2.2.1: Create Config Service
**Lines**: 1-400

**Subtasks**:
1. **Line 1-200**: Service class
   ```typescript
   import { ClientConfiguration, ConfigSyncStatus, ConfigConflict } from '@/types/config';
   import { fetchWithAuth } from '@/context/AuthContext';
   
   const CONFIG_STORAGE_KEY = 'creditnexus_client_config';
   const CONFIG_VERSION_KEY = 'creditnexus_config_version';
   
   export class ConfigService {
     private static instance: ConfigService;
     private config: ClientConfiguration | null = null;
     private schema: any = null;
     
     private constructor() {
       this.loadFromStorage();
     }
     
     static getInstance(): ConfigService {
       if (!ConfigService.instance) {
         ConfigService.instance = new ConfigService();
       }
       return ConfigService.instance;
     }
     
     async loadSchema(): Promise<void> {
       try {
         const response = await fetchWithAuth('/api/config/schema');
         if (response.ok) {
           this.schema = await response.json();
         }
       } catch (error) {
         console.error('Failed to load config schema:', error);
       }
     }
     
     async syncWithServer(): Promise<ConfigSyncStatus> {
       try {
         const response = await fetchWithAuth('/api/config/sync', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             client_config: this.config,
             client_version: localStorage.getItem(CONFIG_VERSION_KEY) || '1.0'
           })
         });
         
         if (response.ok) {
           const result = await response.json();
           
           // Resolve conflicts
           if (result.conflicts && result.conflicts.length > 0) {
             // Auto-resolve: prefer server for synced fields, client for client-only
             for (const conflict of result.conflicts) {
               const field = this.schema?.fields.find((f: any) => f.server_key === conflict.field);
               if (field?.scope === 'synced') {
                 // Use server value
                 this.setConfigValue(conflict.field, conflict.server_value);
               }
             }
           }
           
           // Update config from server
           if (result.server_config) {
             this.config = { ...this.config, ...result.server_config };
             this.saveToStorage();
           }
           
           return result;
         }
       } catch (error) {
         console.error('Failed to sync config:', error);
       }
       
       return {
         last_synced: null,
         server_version: 'unknown',
         client_version: localStorage.getItem(CONFIG_VERSION_KEY) || '1.0',
         conflicts: []
       };
     }
     
     getConfig(): ClientConfiguration {
       if (!this.config) {
         this.config = this.getDefaultConfig();
       }
       return this.config;
     }
     
     setConfigValue(key: string, value: any): void {
       if (!this.config) {
         this.config = this.getDefaultConfig();
       }
       
       const keys = key.split('.');
       let current: any = this.config;
       
       for (let i = 0; i < keys.length - 1; i++) {
         if (!current[keys[i]]) {
           current[keys[i]] = {};
         }
         current = current[keys[i]];
       }
       
       current[keys[keys.length - 1]] = value;
       this.saveToStorage();
     }
     
     getConfigValue(key: string): any {
       if (!this.config) {
         this.config = this.getDefaultConfig();
       }
       
       const keys = key.split('.');
       let current: any = this.config;
       
       for (const k of keys) {
         if (current && typeof current === 'object' && k in current) {
           current = current[k];
         } else {
           return undefined;
         }
       }
       
       return current;
     }
     
     private getDefaultConfig(): ClientConfiguration {
       return {
         llm: {
           provider: 'openai',
           model: 'gpt-4o',
           temperature: 0.0
         },
         commission: {
           enabled: true,
           default_rate: 0.5
         },
         trading: {
           enabled: true
         },
         ui: {
           theme: 'system',
           sidebar_collapsed: false
         },
         features: {}
       };
     }
     
     private loadFromStorage(): void {
       try {
         const stored = localStorage.getItem(CONFIG_STORAGE_KEY);
         if (stored) {
           this.config = JSON.parse(stored);
         }
       } catch (error) {
         console.error('Failed to load config from storage:', error);
       }
     }
     
     private saveToStorage(): void {
       try {
         localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(this.config));
         localStorage.setItem(CONFIG_VERSION_KEY, '1.0');
       } catch (error) {
         console.error('Failed to save config to storage:', error);
       }
     }
     
     validateConfig(): { valid: boolean; errors: string[] } {
       const errors: string[] = [];
       
       if (!this.config) {
         return { valid: false, errors: ['Configuration not loaded'] };
       }
       
       // Validate required fields
       if (!this.config.llm?.provider) {
         errors.push('LLM provider is required');
       }
       
       if (!this.config.llm?.model) {
         errors.push('LLM model is required');
       }
       
       // Validate ranges
       if (this.config.llm?.temperature !== undefined) {
         if (this.config.llm.temperature < 0 || this.config.llm.temperature > 1) {
           errors.push('LLM temperature must be between 0 and 1');
         }
       }
       
       if (this.config.commission?.default_rate !== undefined) {
         if (this.config.commission.default_rate < 0 || this.config.commission.default_rate > 100) {
           errors.push('Commission rate must be between 0 and 100');
         }
       }
       
       return {
         valid: errors.length === 0,
         errors
       };
     }
   }
   
   export const configService = ConfigService.getInstance();
   ```

---

## Project 3: Configuration Sync & Validation

### Activity 3.1: Server Config Sync Endpoint

**File**: `app/api/config_routes.py` (UPDATE)

#### Task 3.1.1: Add Config Sync Endpoint
**Lines**: ~100-300

**Subtasks**:
1. **Line 100-200**: Sync endpoint
   ```python
   @router.post("/config/sync")
   async def sync_config(
       request: ConfigSyncRequest,
       current_user: User = Depends(require_auth),
       db: Session = Depends(get_db)
   ):
       """Sync client configuration with server.
       
       Validates client config against server config schema,
       identifies conflicts, and returns server config for synced fields.
       """
       from app.core.config_schema import generate_config_schema
       from app.core.config import settings
       
       schema = generate_config_schema()
       client_config = request.client_config
       conflicts = []
       server_config = {}
       
       # Get client-visible fields
       client_fields = schema.get_client_config()
       
       for field in client_fields:
           if field.scope == ConfigScope.SYNCED:
               # Get server value
               server_value = getattr(settings, field.server_key, None)
               
               # Get client value
               client_value = _get_nested_value(client_config, field.client_key) if field.client_key else None
               
               # Check for conflicts
               if client_value is not None and client_value != server_value:
                   conflicts.append({
                       "field": field.server_key,
                       "server_value": server_value,
                       "client_value": client_value,
                       "resolution": "server"  # Prefer server for synced fields
                   })
               
               # Always use server value for synced fields
               server_config[field.client_key] = server_value
           elif field.scope == ConfigScope.SHARED:
               # Both can have values, but validate client value
               client_value = _get_nested_value(client_config, field.client_key) if field.client_key else None
               server_value = getattr(settings, field.server_key, None)
               
               # Validate client value
               if client_value is not None:
                   validation_result = _validate_field_value(field, client_value)
                   if not validation_result["valid"]:
                       conflicts.append({
                           "field": field.server_key,
                           "server_value": server_value,
                           "client_value": client_value,
                           "resolution": "server",
                           "error": validation_result["error"]
                       })
                       server_config[field.client_key] = server_value
                   else:
                       server_config[field.client_key] = client_value
       
       return {
           "status": "success",
           "server_config": server_config,
           "conflicts": conflicts,
           "server_version": "1.0",
           "last_synced": datetime.utcnow().isoformat()
       }
   
   @router.get("/config/schema")
   async def get_config_schema(
       current_user: User = Depends(require_auth)
   ):
       """Get configuration schema for client."""
       from app.core.config_schema import generate_config_schema
       
       schema = generate_config_schema()
       return {
           "version": schema.version,
           "fields": [
               {
                   "name": f.name,
                   "category": f.category.value,
                   "scope": f.scope.value,
                   "field_type": f.field_type.value,
                   "description": f.description,
                   "default_value": f.default_value,
                   "required": f.required,
                   "server_key": f.server_key,
                   "client_key": f.client_key,
                   "validation_rules": f.validation_rules,
                   "enum_values": f.enum_values,
                   "min_value": f.min_value,
                   "max_value": f.max_value,
                   "ui_component": f.ui_component,
                   "ai_editable": f.ai_editable,
                   "depends_on": f.depends_on,
                   "affects": f.affects
               }
               for f in schema.fields
           ]
       }
   ```

---

## Project 4: Setup & Configure Scripts

### Activity 4.1: Client Setup Script

**File**: `scripts/setup-client.sh` (NEW)

#### Task 4.1.1: Create Setup Script
**Lines**: 1-200

**Subtasks**:
1. **Line 1-100**: Setup script
   ```bash
   #!/bin/bash
   # CreditNexus Client Setup Script
   
   set -e
   
   echo "CreditNexus Client Setup"
   echo "========================"
   echo ""
   
   # Check Node.js
   if ! command -v node &> /dev/null; then
       echo "❌ Node.js is not installed. Please install Node.js 18+ first."
       exit 1
   fi
   
   NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
   if [ "$NODE_VERSION" -lt 18 ]; then
       echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
       exit 1
   fi
   
   echo "✅ Node.js $(node -v) detected"
   
   # Check npm
   if ! command -v npm &> /dev/null; then
       echo "❌ npm is not installed."
       exit 1
   fi
   
   echo "✅ npm $(npm -v) detected"
   echo ""
   
   # Install dependencies
   echo "Installing dependencies..."
   cd client
   npm install
   echo "✅ Dependencies installed"
   echo ""
   
   # Run configuration wizard
   echo "Starting configuration wizard..."
   node scripts/configure-client.js
   echo ""
   
   # Build client
   echo "Building client..."
   npm run build
   echo "✅ Client built successfully"
   echo ""
   
   echo "Setup complete! Run 'npm run dev' to start the development server."
   ```

### Activity 4.2: Configuration Wizard

**File**: `client/scripts/configure-client.js` (NEW)

#### Task 4.2.1: Create Config Wizard
**Lines**: 1-400

**Subtasks**:
1. **Line 1-200**: Interactive wizard
   ```javascript
   #!/usr/bin/env node
   
   const readline = require('readline');
   const fs = require('fs');
   const path = require('path');
   
   const rl = readline.createInterface({
     input: process.stdin,
     output: process.stdout
   });
   
   function question(prompt) {
     return new Promise((resolve) => {
       rl.question(prompt, resolve);
     });
   }
   
   async function configureClient() {
     console.log('CreditNexus Client Configuration Wizard');
     console.log('=====================================\n');
     
     const config = {
       server: {
         url: '',
         api_key: ''
       },
       llm: {
         provider: 'openai',
         model: 'gpt-4o',
         temperature: 0.0
       },
       commission: {
         enabled: true,
         default_rate: 0.5
       },
       trading: {
         enabled: true
       },
       ui: {
         theme: 'system',
         sidebar_collapsed: false
       }
     };
     
     // Server URL
     const serverUrl = await question('Server URL (default: http://localhost:8000): ');
     config.server.url = serverUrl || 'http://localhost:8000';
     
     // LLM Provider
     console.log('\nLLM Provider:');
     console.log('1. OpenAI (default)');
     console.log('2. vLLM');
     console.log('3. HuggingFace');
     const llmChoice = await question('Select LLM provider (1-3, default: 1): ');
     const llmProviders = { '1': 'openai', '2': 'vllm', '3': 'huggingface' };
     config.llm.provider = llmProviders[llmChoice] || 'openai';
     
     // LLM Model
     const model = await question(`LLM Model (default: ${config.llm.model}): `);
     if (model) {
       config.llm.model = model;
     }
     
     // Commission
     const commissionEnabled = await question('Enable commission for trades? (y/n, default: y): ');
     config.commission.enabled = commissionEnabled.toLowerCase() !== 'n';
     
     if (config.commission.enabled) {
       const rate = await question('Default commission rate (%) (default: 0.5): ');
       config.commission.default_rate = parseFloat(rate) || 0.5;
     }
     
     // Trading
     const tradingEnabled = await question('Enable trading functionality? (y/n, default: y): ');
     config.trading.enabled = tradingEnabled.toLowerCase() !== 'n';
     
     // Save config
     const configPath = path.join(__dirname, '..', 'src', 'config', 'client-config.json');
     const configDir = path.dirname(configPath);
     
     if (!fs.existsSync(configDir)) {
       fs.mkdirSync(configDir, { recursive: true });
     }
     
     fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
     
     console.log('\n✅ Configuration saved to:', configPath);
     console.log('\nConfiguration complete!');
     
     rl.close();
   }
   
   configureClient().catch(console.error);
   ```

### Activity 4.3: PowerShell Setup Script

**File**: `scripts/setup-client.ps1` (NEW)

#### Task 4.3.1: Create PowerShell Script
**Lines**: 1-200

**Subtasks**:
1. **Line 1-200**: PowerShell script
   ```powershell
   # CreditNexus Client Setup Script (PowerShell)
   
   Write-Host "CreditNexus Client Setup" -ForegroundColor Cyan
   Write-Host "========================" -ForegroundColor Cyan
   Write-Host ""
   
   # Check Node.js
   if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
       Write-Host "❌ Node.js is not installed. Please install Node.js 18+ first." -ForegroundColor Red
       exit 1
   }
   
   $nodeVersion = (node -v).Substring(1).Split('.')[0]
   if ([int]$nodeVersion -lt 18) {
       Write-Host "❌ Node.js version 18+ is required. Current version: $(node -v)" -ForegroundColor Red
       exit 1
   }
   
   Write-Host "✅ Node.js $(node -v) detected" -ForegroundColor Green
   
   # Check npm
   if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
       Write-Host "❌ npm is not installed." -ForegroundColor Red
       exit 1
   }
   
   Write-Host "✅ npm $(npm -v) detected" -ForegroundColor Green
   Write-Host ""
   
   # Install dependencies
   Write-Host "Installing dependencies..." -ForegroundColor Yellow
   Set-Location client
   npm install
   Write-Host "✅ Dependencies installed" -ForegroundColor Green
   Write-Host ""
   
   # Run configuration wizard
   Write-Host "Starting configuration wizard..." -ForegroundColor Yellow
   node scripts/configure-client.js
   Write-Host ""
   
   # Build client
   Write-Host "Building client..." -ForegroundColor Yellow
   npm run build
   Write-Host "✅ Client built successfully" -ForegroundColor Green
   Write-Host ""
   
   Write-Host "Setup complete! Run 'npm run dev' to start the development server." -ForegroundColor Cyan
   ```

---

## Project 5: AI-Assisted Configuration UI

### Activity 5.1: Configuration Dashboard Component

**File**: `client/src/components/dashboard-tabs/ConfigurationDashboard.tsx` (NEW)

#### Task 5.1.1: Create Config Dashboard
**Lines**: 1-800

**Subtasks**:
1. **Line 1-300**: Component setup
   ```typescript
   import { useState, useEffect } from 'react';
   import { Settings, Plus, Trash2, Sparkles, CheckCircle2, XCircle } from 'lucide-react';
   import { configService } from '@/services/configService';
   import { ConfigFieldMetadata, ConfigCategory } from '@/types/config';
   import { Button } from '@/components/ui/button';
   import { Card } from '@/components/ui/card';
   import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
   import { Input } from '@/components/ui/input';
   import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
   import { Checkbox } from '@/components/ui/checkbox';
   import { AiConfigEditor } from '@/components/config/AiConfigEditor';
   
   export function ConfigurationDashboard() {
     const [schema, setSchema] = useState<any>(null);
     const [config, setConfig] = useState(configService.getConfig());
     const [loading, setLoading] = useState(false);
     const [syncStatus, setSyncStatus] = useState<any>(null);
     const [selectedCategory, setSelectedCategory] = useState<ConfigCategory>(ConfigCategory.LLM);
     
     useEffect(() => {
       loadSchema();
       syncConfig();
     }, []);
     
     const loadSchema = async () => {
       try {
         await configService.loadSchema();
         // Schema loaded in service
       } catch (error) {
         console.error('Failed to load schema:', error);
       }
     };
     
     const syncConfig = async () => {
       setLoading(true);
       try {
         const status = await configService.syncWithServer();
         setSyncStatus(status);
         setConfig(configService.getConfig());
       } catch (error) {
         console.error('Failed to sync config:', error);
       } finally {
         setLoading(false);
       }
     };
     
     const handleConfigChange = (key: string, value: any) => {
       configService.setConfigValue(key, value);
       setConfig(configService.getConfig());
     };
     
     const categories = [
       ConfigCategory.LLM,
       ConfigCategory.COMMISSION,
       ConfigCategory.TRADING,
       ConfigCategory.POLICY,
       ConfigCategory.BLOCKCHAIN,
       ConfigCategory.PAYMENT,
       ConfigCategory.UI,
       ConfigCategory.FEATURE_FLAG
     ];
     
     const getFieldsByCategory = (category: ConfigCategory): ConfigFieldMetadata[] => {
       if (!schema) return [];
       return schema.fields.filter((f: ConfigFieldMetadata) => f.category === category);
     };
     
     return (
       <div className="space-y-6">
         <div className="flex items-center justify-between">
           <div>
             <h2 className="text-2xl font-semibold text-slate-100 mb-2">
               Configuration
             </h2>
             <p className="text-slate-400">
               Manage client and server configuration settings
             </p>
           </div>
           <div className="flex items-center gap-2">
             <Button
               onClick={syncConfig}
               disabled={loading}
               variant="outline"
             >
               {loading ? 'Syncing...' : 'Sync with Server'}
             </Button>
             {syncStatus && (
               <div className="text-sm text-slate-400">
                 Last synced: {syncStatus.last_synced ? new Date(syncStatus.last_synced).toLocaleString() : 'Never'}
               </div>
             )}
           </div>
         </div>
         
         {syncStatus?.conflicts && syncStatus.conflicts.length > 0 && (
           <Card className="p-4 bg-yellow-900/20 border-yellow-500/50">
             <h3 className="font-semibold text-yellow-400 mb-2">Configuration Conflicts</h3>
             <div className="space-y-2">
               {syncStatus.conflicts.map((conflict: any, idx: number) => (
                 <div key={idx} className="text-sm">
                   <span className="text-slate-300">{conflict.field}:</span>
                   <span className="text-yellow-400 ml-2">
                     Server: {JSON.stringify(conflict.server_value)} | 
                     Client: {JSON.stringify(conflict.client_value)}
                   </span>
                 </div>
               ))}
             </div>
           </Card>
         )}
         
         <Tabs defaultValue={selectedCategory} onValueChange={(v) => setSelectedCategory(v as ConfigCategory)}>
           <TabsList className="grid w-full grid-cols-4">
             {categories.slice(0, 4).map((cat) => (
               <TabsTrigger key={cat} value={cat}>
                 {cat.replace('_', ' ').toUpperCase()}
               </TabsTrigger>
             ))}
           </TabsList>
           
           {categories.map((category) => (
             <TabsContent key={category} value={category} className="space-y-4">
               <Card className="p-6">
                 <h3 className="text-lg font-semibold mb-4">
                   {category.replace('_', ' ').toUpperCase()} Configuration
                 </h3>
                 <div className="space-y-4">
                   {getFieldsByCategory(category).map((field) => (
                     <ConfigFieldEditor
                       key={field.server_key}
                       field={field}
                       value={configService.getConfigValue(field.client_key || field.server_key)}
                       onChange={(value) => handleConfigChange(field.client_key || field.server_key, value)}
                     />
                   ))}
                 </div>
               </Card>
             </TabsContent>
           ))}
         </Tabs>
       </div>
     );
   }
   ```

2. **Line 301-500**: Config Field Editor
   ```typescript
   interface ConfigFieldEditorProps {
     field: ConfigFieldMetadata;
     value: any;
     onChange: (value: any) => void;
   }
   
   function ConfigFieldEditor({ field, value, onChange }: ConfigFieldEditorProps) {
     const [aiEditing, setAiEditing] = useState(false);
     
     if (field.ui_component === 'ai_assist' || field.ai_editable) {
       return (
         <div className="space-y-2">
           <div className="flex items-center justify-between">
             <div>
               <label className="text-sm font-medium text-slate-300">{field.name}</label>
               <p className="text-xs text-slate-500">{field.description}</p>
             </div>
             <Button
               variant="ghost"
               size="sm"
               onClick={() => setAiEditing(true)}
             >
               <Sparkles className="h-4 w-4 mr-2" />
               AI Assist
             </Button>
           </div>
           {aiEditing ? (
             <AiConfigEditor
               field={field}
               currentValue={value}
               onSave={(newValue) => {
                 onChange(newValue);
                 setAiEditing(false);
               }}
               onCancel={() => setAiEditing(false)}
             />
           ) : (
             <Input
               value={value || field.default_value || ''}
               onChange={(e) => onChange(e.target.value)}
               className="bg-slate-900 border-slate-700"
             />
           )}
         </div>
       );
     }
     
     if (field.field_type === ConfigFieldType.BOOLEAN) {
       return (
         <div className="flex items-center justify-between">
           <div>
             <label className="text-sm font-medium text-slate-300">{field.name}</label>
             <p className="text-xs text-slate-500">{field.description}</p>
           </div>
           <Checkbox
             checked={value ?? field.default_value ?? false}
             onCheckedChange={(checked) => onChange(checked)}
           />
         </div>
       );
     }
     
     if (field.field_type === ConfigFieldType.ENUM) {
       return (
         <div className="space-y-2">
           <label className="text-sm font-medium text-slate-300">{field.name}</label>
           <p className="text-xs text-slate-500">{field.description}</p>
           <Select
             value={value || field.default_value || ''}
             onValueChange={onChange}
           >
             <SelectTrigger className="bg-slate-900 border-slate-700">
               <SelectValue />
             </SelectTrigger>
             <SelectContent>
               {field.enum_values?.map((val) => (
                 <SelectItem key={val} value={val}>
                   {val}
                 </SelectItem>
               ))}
             </SelectContent>
           </Select>
         </div>
       );
     }
     
     return (
       <div className="space-y-2">
         <label className="text-sm font-medium text-slate-300">{field.name}</label>
         <p className="text-xs text-slate-500">{field.description}</p>
         <Input
           type={field.field_type === ConfigFieldType.INTEGER || field.field_type === ConfigFieldType.FLOAT ? 'number' : 'text'}
           value={value || field.default_value || ''}
           onChange={(e) => onChange(e.target.value)}
           min={field.min_value}
           max={field.max_value}
           className="bg-slate-900 border-slate-700"
         />
       </div>
     );
   }
   ```

### Activity 5.2: AI Config Editor Component (Admin Only)

**File**: `client/src/components/config/AiConfigEditor.tsx` (NEW)

#### Task 5.2.1: Create AI Editor (Admin Only)
**Lines**: 1-450

**Subtasks**:
1. **Line 1-450**: AI-assisted editor with admin check
   ```typescript
   import { useState, useEffect } from 'react';
   import { Sparkles, CheckCircle2, XCircle, Shield } from 'lucide-react';
   import { ConfigFieldMetadata } from '@/types/config';
   import { Button } from '@/components/ui/button';
   import { Textarea } from '@/components/ui/textarea';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { useAuth } from '@/context/AuthContext';
   import { Alert, AlertDescription } from '@/components/ui/alert';
   
   interface AiConfigEditorProps {
     field: ConfigFieldMetadata;
     currentValue: any;
     onSave: (value: any) => void;
     onCancel: () => void;
   }
   
   export function AiConfigEditor({ field, currentValue, onSave, onCancel }: AiConfigEditorProps) {
     const { user } = useAuth();
     const [isAdmin, setIsAdmin] = useState(false);
     const [checkingAdmin, setCheckingAdmin] = useState(true);
     const [instruction, setInstruction] = useState('');
     const [loading, setLoading] = useState(false);
     const [suggestedValue, setSuggestedValue] = useState<any>(null);
     const [error, setError] = useState<string | null>(null);
     
     // Check admin access
     useEffect(() => {
       if (user?.role !== 'admin') {
         setIsAdmin(false);
       } else {
         setIsAdmin(true);
       }
     }, [user]);
     
     const handleAiEdit = async () => {
       if (!isAdmin) {
         setError('Only administrators can use AI-assisted editing');
         return;
       }
       
       setLoading(true);
       setError(null);
       
       try {
         const response = await fetchWithAuth('/api/config/ai-edit', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             field_key: field.server_key,
             field_type: field.field_type,
             current_value: currentValue,
             instruction: instruction,
             field_metadata: {
               description: field.description,
               enum_values: field.enum_values,
               min_value: field.min_value,
               max_value: field.max_value,
               validation_rules: field.validation_rules
             }
           })
         });
         
         if (response.ok) {
           const result = await response.json();
           setSuggestedValue(result.suggested_value);
         } else {
           setError('Failed to generate suggestion');
         }
       } catch (err) {
         setError(err instanceof Error ? err.message : 'Unknown error');
       } finally {
         setLoading(false);
       }
     };
     
     if (!isAdmin) {
       return (
         <Alert className="bg-yellow-900/20 border-yellow-500/50">
           <Shield className="h-4 w-4 text-yellow-400" />
           <AlertDescription className="text-yellow-400">
             AI-assisted configuration editing is only available to administrators.
           </AlertDescription>
         </Alert>
       );
     }
     
     return (
       <div className="space-y-4 p-4 border border-slate-700 rounded-lg bg-slate-900/50">
         <div className="flex items-center gap-2">
           <Sparkles className="h-5 w-5 text-emerald-400" />
           <h4 className="font-semibold text-slate-100">AI-Assisted Configuration (Admin Only)</h4>
         </div>
         
         <div className="space-y-2">
           <label className="text-sm font-medium text-slate-300">
             Current Value
           </label>
           <div className="p-2 bg-slate-800 rounded text-sm text-slate-400">
             {JSON.stringify(currentValue || field.default_value || 'Not set')}
           </div>
         </div>
         
         <div className="space-y-2">
           <label className="text-sm font-medium text-slate-300">
             Instruction (e.g., "Set temperature to 0.7 for more creative responses")
           </label>
           <Textarea
             value={instruction}
             onChange={(e) => setInstruction(e.target.value)}
             placeholder="Describe the change you want to make..."
             className="bg-slate-900 border-slate-700 text-slate-100"
             rows={3}
           />
         </div>
         
         <Button
           onClick={handleAiEdit}
           disabled={loading || !instruction.trim()}
           className="w-full"
         >
           {loading ? 'Generating...' : 'Generate Suggestion'}
         </Button>
         
         {error && (
           <div className="p-2 bg-red-900/20 border border-red-500/50 rounded text-sm text-red-400">
             {error}
           </div>
         )}
         
         {suggestedValue !== null && (
           <div className="space-y-2">
             <label className="text-sm font-medium text-slate-300">
               Suggested Value
             </label>
             <div className="p-2 bg-emerald-900/20 border border-emerald-500/50 rounded text-sm text-emerald-400">
               {JSON.stringify(suggestedValue)}
             </div>
             <div className="flex gap-2">
               <Button
                 onClick={() => onSave(suggestedValue)}
                 className="flex-1"
               >
                 <CheckCircle2 className="h-4 w-4 mr-2" />
                 Apply
               </Button>
               <Button
                 onClick={onCancel}
                 variant="outline"
                 className="flex-1"
               >
                 <XCircle className="h-4 w-4 mr-2" />
                 Cancel
               </Button>
             </div>
           </div>
         )}
       </div>
     );
   }
   ```

### Activity 5.3: AI Config Edit Endpoint

**File**: `app/api/config_routes.py` (UPDATE)

#### Task 5.3.1: Add AI Edit Endpoint
**Lines**: ~300-500

**Subtasks**:
1. **Line 300-500**: AI edit endpoint
   ```python
   @router.post("/config/ai-edit")
   async def ai_edit_config(
       request: AiConfigEditRequest,
       current_user: User = Depends(require_auth),
       db: Session = Depends(get_db)
   ):
       """AI-assisted configuration editing using add/remove clause patterns (admin only)."""
       # Check admin role
       if current_user.role != UserRole.ADMIN.value:
           raise HTTPException(
               status_code=status.HTTP_403_FORBIDDEN,
               detail="Only administrators can use AI-assisted configuration editing"
           )
       
       from app.chains.config_edit_chain import create_config_edit_chain, create_config_edit_prompt
       
       try:
           chain = create_config_edit_chain()
           prompt = create_config_edit_prompt()
           
           result = chain.invoke(prompt.format_messages(
               field_key=request.field_key,
               field_type=request.field_type,
               current_value=json.dumps(request.current_value) if request.current_value else "null",
               instruction=request.instruction,
               field_metadata=json.dumps(request.field_metadata, default=str),
               validation_rules=json.dumps(request.field_metadata.get("validation_rules", {}), default=str)
           ))
           
           # Validate suggested value
           validation_result = _validate_field_value_from_metadata(
               request.field_metadata,
               result.suggested_value
           )
           
           if not validation_result["valid"]:
               return {
                   "status": "error",
                   "error": validation_result["error"],
                   "suggested_value": None
               }
           
           return {
               "status": "success",
               "suggested_value": result.suggested_value,
               "reasoning": result.reasoning,
               "confidence": result.confidence
           }
       except Exception as e:
           logger.error(f"Error in AI config edit: {e}", exc_info=True)
           raise HTTPException(
               status_code=500,
               detail=f"Failed to generate config suggestion: {str(e)}"
           )
   ```

---

## Project 6: Configuration Validation & Compatibility

### Activity 6.1: Compatibility Checker

**File**: `app/services/config_compatibility_service.py` (NEW)

#### Task 6.1.1: Create Compatibility Service
**Lines**: 1-300

**Subtasks**:
1. **Line 1-300**: Compatibility checker
   ```python
   class ConfigCompatibilityService:
       """Service for checking client-server configuration compatibility."""
       
       def __init__(self, db: Session):
           self.db = db
       
       def check_compatibility(
           self,
           client_config: Dict[str, Any],
           server_config: Optional[Dict[str, Any]] = None
       ) -> Dict[str, Any]:
           """Check compatibility between client and server config.
           
           Args:
               client_config: Client configuration dictionary
               server_config: Server configuration (optional, will load from settings if not provided)
               
           Returns:
               Compatibility report with issues and recommendations
           """
           from app.core.config_schema import generate_config_schema
           from app.core.config import settings
           
           if server_config is None:
               server_config = self._extract_server_config(settings)
           
           schema = generate_config_schema()
           issues = []
           warnings = []
           
           # Check each client-visible field
           client_fields = schema.get_client_config()
           
           for field in client_fields:
               client_value = _get_nested_value(client_config, field.client_key) if field.client_key else None
               
               if field.scope == ConfigScope.SYNCED:
                   # Synced fields must match server
                   server_value = getattr(settings, field.server_key, None)
                   if client_value != server_value:
                       issues.append({
                           "field": field.server_key,
                           "type": "mismatch",
                           "message": f"Client value ({client_value}) does not match server value ({server_value})",
                           "severity": "error",
                           "resolution": "Use server value"
                       })
               
               elif field.scope == ConfigScope.SHARED:
                   # Shared fields should be validated
                   if client_value is not None:
                       validation = _validate_field_value(field, client_value)
                       if not validation["valid"]:
                           issues.append({
                               "field": field.server_key,
                               "type": "validation",
                               "message": validation["error"],
                               "severity": "error",
                               "resolution": "Fix client value"
                           })
                   
                   # Check if client value is compatible with server
                   server_value = getattr(settings, field.server_key, None)
                   if client_value is not None and server_value is not None:
                       if not self._are_values_compatible(field, client_value, server_value):
                           warnings.append({
                               "field": field.server_key,
                               "type": "incompatibility",
                               "message": f"Client and server values may not work together",
                               "severity": "warning"
                           })
               
               # Check dependencies
               if field.depends_on:
                   for dep in field.depends_on:
                       dep_value = _get_nested_value(client_config, dep) if dep in client_config else None
                       if dep_value is None:
                           warnings.append({
                               "field": field.server_key,
                               "type": "missing_dependency",
                               "message": f"Depends on {dep} which is not set",
                               "severity": "warning"
                           })
           
           return {
               "compatible": len(issues) == 0,
               "issues": issues,
               "warnings": warnings,
               "recommendations": self._generate_recommendations(issues, warnings)
           }
       
       def _are_values_compatible(
           self,
           field: ConfigFieldMetadata,
           client_value: Any,
           server_value: Any
       ) -> bool:
           """Check if client and server values are compatible."""
           # Example: If LLM provider is different, they're incompatible
           if field.server_key == "LLM_PROVIDER":
               return client_value == server_value
           
           # For most fields, any value is compatible
           return True
       
       def _generate_recommendations(
           self,
           issues: List[Dict[str, Any]],
           warnings: List[Dict[str, Any]]
       ) -> List[str]:
           """Generate recommendations based on issues and warnings."""
           recommendations = []
           
           if any(i["type"] == "mismatch" for i in issues):
               recommendations.append("Sync configuration with server to resolve mismatches")
           
           if any(i["type"] == "validation" for i in issues):
               recommendations.append("Fix validation errors in client configuration")
           
           if any(w["type"] == "incompatibility" for w in warnings):
               recommendations.append("Review incompatible values and align with server settings")
           
           return recommendations
   ```

---

## Implementation Checklist

### Phase 1: Configuration Inventory (Week 1)
- [ ] Create configuration schema system
- [ ] Generate schema from Settings class
- [ ] Categorize all configuration fields
- [ ] Document all configuration options

### Phase 2: Client Configuration System (Week 2)
- [ ] Create client configuration types
- [ ] Implement ConfigService
- [ ] Add localStorage persistence
- [ ] Implement configuration validation

### Phase 3: Configuration Sync (Week 3)
- [ ] Add config sync endpoint
- [ ] Implement conflict detection
- [ ] Add auto-resolution logic
- [ ] Test client-server sync

### Phase 4: Setup Scripts (Week 4)
- [ ] Create bash setup script
- [ ] Create PowerShell setup script
- [ ] Create configuration wizard
- [ ] Test setup scripts

### Phase 5: Configuration UI (Week 5-6)
- [ ] Create ConfigurationDashboard component
- [ ] Implement ConfigFieldEditor
- [ ] Add category tabs
- [ ] Add sync status display

### Phase 6: AI-Assisted Editing (Week 7)
- [ ] Create AiConfigEditor component (admin-only)
- [ ] Implement config edit chain
- [ ] Add AI edit endpoint (admin-only)
- [ ] Add admin role checks
- [ ] Test AI editing flow

### Phase 7: Organization Policies (Week 8)
- [ ] Create OrganizationPolicy models
- [ ] Create OrganizationPolicyService
- [ ] Add policy initialization from defaults
- [ ] Add policy customization
- [ ] Add policy versioning
- [ ] Add organization policy API endpoints

### Phase 8: AI Policy Decision Editing (Week 9)
- [ ] Create PolicyDecisionEditor component (admin-only)
- [ ] Create AiPolicyDecisionEditor component
- [ ] Implement policy decision edit chain
- [ ] Add AI policy decision edit endpoint (admin-only)
- [ ] Test policy decision editing flow

### Phase 9: Compatibility & Validation (Week 10)
- [ ] Create compatibility checker
- [ ] Add pre-connection validation
- [ ] Implement recommendations
- [ ] Test compatibility checks

---

## Key Design Decisions

### 1. Commission-Based Trading
- **Users execute trades themselves** (not on behalf)
- **CreditNexus takes commission** on executed trades
- Configuration: `ALLOW_TRADE_ON_BEHALF=false` (default)
- Commission calculated after trade execution

### 2. Configuration Scopes
- **SERVER_ONLY**: Only on server (API keys, secrets)
- **CLIENT_ONLY**: Only on client (UI preferences)
- **SHARED**: Both can have values (LLM settings)
- **SYNCED**: Server value synced to client (feature flags)

### 3. AI-Assisted Editing (Admin Only)
- Uses "add clause" / "remove clause" patterns
- Validates suggestions before applying
- Provides reasoning and confidence scores
- Only for `ai_editable=true` fields
- **Admin role required** for all AI-assisted editing
- Includes policy decision editing with AI assistance

### 4. Organization-Specific Policies
- Organizations inherit default policies on creation
- Policies can be customized per organization
- Version history for policy changes
- Update from defaults to get latest changes
- Admin-only policy management

### 5. Compatibility Validation
- Pre-connection validation
- Automatic conflict resolution
- Recommendations for fixes
- Warnings for potential issues

---

## Success Criteria

1. ✅ All configuration options inventoried and categorized
2. ✅ Client-server configuration compatibility verified
3. ✅ Setup scripts work on Windows and Unix
4. ✅ Configuration UI with **admin-only** AI assistance
5. ✅ Automatic sync and conflict resolution
6. ✅ Pre-connection validation
7. ✅ Commission system configured correctly
8. ✅ Trading enabled (users execute, CreditNexus takes commission)
9. ✅ Organization-specific policies with defaults
10. ✅ AI-assisted policy decision editing (admin-only)
11. ✅ Policy versioning and history

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
