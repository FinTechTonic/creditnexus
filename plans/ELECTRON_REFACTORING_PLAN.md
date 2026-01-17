# CreditNexus Electron Desktop Application & Complete Refactoring Plan
## Unified Implementation with Electron, Multi-Feature Integration, and Client-Server Architecture

**Status**: Comprehensive Refactoring Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 16-20 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This document provides a **complete refactoring plan** for transforming CreditNexus into a unified Electron desktop application with:
- **Electron Wrapper**: Native .exe builds with CI/CD pipeline
- **Client-Server Architecture**: Clear separation between Electron client and FastAPI server
- **Unified Dashboard**: Single permissioned dashboard with tab-based navigation
- **Multi-Feature Integration**: Polymarket, Trading Dashboard, DigiSign, and all existing features
- **Enhanced Authentication**: Verified implementations selection in login/signup
- **New Roles & Permissions**: Trader, Compliance Officer, User Dashboard roles
- **Flexible Subscriptions**: Pro (pay-as-you-go), Lifetime payments
- **Configurable Fees**: Per-deal, per-workflow, per-payment-type commission system
- **Setup Automation**: Cross-platform setup scripts (bash/PowerShell)
- **FDC3/OpenFin Compliance**: Full desktop interoperability support

**Key Architectural Changes:**
- Electron main process handles window management and IPC
- React renderer process for UI (existing client code)
- FastAPI server runs as separate process (can be local or remote)
- IPC bridge between Electron and server
- Unified dashboard replaces multiple app views
- Permission-based tab visibility
- Subscription tier enforcement at API and UI levels

---

## Current State Analysis

### ✅ Existing Infrastructure

#### 1. Frontend Architecture
**Location**: `client/src/`
- React 18 with TypeScript
- Vite build system
- FDC3 2.0 integration (`client/src/context/FDC3Context.tsx`)
- OpenFin manifest (`openfin/app.json`)
- Multiple app views in `DesktopAppLayout.tsx`
- Permission system (`client/src/utils/permissions.ts`)

**Gaps**:
- No Electron configuration
- No unified dashboard (multiple separate views)
- No verified implementations selection in auth
- No subscription tier enforcement in UI
- No commission/fee configuration UI

#### 2. Backend Architecture
**Location**: `server.py`, `app/`
- FastAPI with SQLAlchemy 2.0
- JWT authentication (`app/auth/jwt_auth.py`)
- Permission system (`app/core/permissions.py`)
- x402 payment service (`app/services/x402_payment_service.py`)
- Policy engine integration
- CDM compliance

**Gaps**:
- No subscription service (RevenueCat mentioned but not implemented)
- No commission/fee calculation service
- No verified implementations system
- No Electron-specific API endpoints

#### 3. Authentication System
**Location**: `app/auth/jwt_auth.py`, `client/src/context/AuthContext.tsx`
- Email/password login
- MetaMask wallet authentication
- JWT tokens with refresh
- Role-based access control

**Gaps**:
- No verified implementations selection
- No subscription tier in user model
- No lifetime payment tracking

#### 4. Database Models
**Location**: `app/db/models.py`
- User model with roles
- PaymentEvent model
- Deal, Document, Trade models

**Gaps**:
- No Subscription model
- No CommissionConfig model
- No VerifiedImplementation model
- No UserSubscription model

---

## Project 1: Electron Desktop Application Setup

### Activity 1.1: Electron Configuration

**File**: `electron/main.js` (NEW)

#### Task 1.1.1: Create Electron Main Process
**Lines**: 1-200

**Subtasks**:
1. **Line 1-50**: Imports and setup
   ```javascript
   const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
   const path = require('path');
   const { spawn } = require('child_process');
   const fs = require('fs');
   const https = require('https');
   const http = require('http');
   
   let mainWindow = null;
   let serverProcess = null;
   const SERVER_PORT = 8000;
   const SERVER_URL = `http://localhost:${SERVER_PORT}`;
   ```

2. **Line 51-100**: Window creation
   ```javascript
   function createWindow() {
     mainWindow = new BrowserWindow({
       width: 1400,
       height: 900,
       minWidth: 1024,
       minHeight: 768,
       webPreferences: {
         nodeIntegration: false,
         contextIsolation: true,
         preload: path.join(__dirname, 'preload.js'),
         webSecurity: true
       },
       icon: path.join(__dirname, '../assets/icon.png'),
       titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
       show: false
     });
     
     // Load app
     if (process.env.NODE_ENV === 'development') {
       mainWindow.loadURL('http://localhost:5173');
       mainWindow.webContents.openDevTools();
     } else {
       mainWindow.loadFile(path.join(__dirname, '../client/dist/index.html'));
     }
     
     mainWindow.once('ready-to-show', () => {
       mainWindow.show();
     });
   }
   ```

3. **Line 101-150**: Server process management
   ```javascript
   function startServer() {
     const serverScript = path.join(__dirname, '../server.py');
     const pythonExecutable = process.platform === 'win32' 
       ? 'python' 
       : 'python3';
     
     serverProcess = spawn(pythonExecutable, [serverScript], {
       cwd: path.join(__dirname, '..'),
       env: { ...process.env, PORT: SERVER_PORT }
     });
     
     serverProcess.stdout.on('data', (data) => {
       console.log(`Server: ${data}`);
     });
     
     serverProcess.stderr.on('data', (data) => {
       console.error(`Server Error: ${data}`);
     });
   }
   
   function stopServer() {
     if (serverProcess) {
       serverProcess.kill();
       serverProcess = null;
     }
   }
   ```

4. **Line 151-200**: IPC handlers and app lifecycle
   ```javascript
   // IPC handlers for client-server communication
   ipcMain.handle('get-server-url', () => SERVER_URL);
   ipcMain.handle('check-server-health', async () => {
     return new Promise((resolve) => {
       http.get(`${SERVER_URL}/api/health`, (res) => {
         resolve(res.statusCode === 200);
       }).on('error', () => resolve(false));
     });
   });
   
   app.whenReady().then(() => {
     startServer();
     createWindow();
     
     app.on('activate', () => {
       if (BrowserWindow.getAllWindows().length === 0) {
         createWindow();
       }
     });
   });
   
   app.on('window-all-closed', () => {
     if (process.platform !== 'darwin') {
       stopServer();
       app.quit();
     }
   });
   
   app.on('before-quit', () => {
     stopServer();
   });
   ```

#### Task 1.1.2: Create Preload Script
**File**: `electron/preload.js` (NEW)

**Lines**: 1-100

**Subtasks**:
1. **Line 1-50**: Expose safe APIs to renderer
   ```javascript
   const { contextBridge, ipcRenderer } = require('electron');
   
   contextBridge.exposeInMainWorld('electronAPI', {
     getServerUrl: () => ipcRenderer.invoke('get-server-url'),
     checkServerHealth: () => ipcRenderer.invoke('check-server-health'),
     openExternal: (url) => ipcRenderer.invoke('open-external', url),
     getVersion: () => ipcRenderer.invoke('get-version'),
     platform: process.platform
   });
   
   // Expose FDC3 if available (for OpenFin compatibility)
   if (typeof window !== 'undefined' && window.fdc3) {
     contextBridge.exposeInMainWorld('fdc3', window.fdc3);
   }
   ```

#### Task 1.1.3: Update Package Configuration
**File**: `package.json` (UPDATE)

**Lines**: Add Electron dependencies and build scripts

**Subtasks**:
1. Add Electron dependencies:
   ```json
   {
     "devDependencies": {
       "electron": "^28.0.0",
       "electron-builder": "^24.9.1",
       "@electron/notarize": "^2.2.0"
     }
   }
   ```

2. Add build scripts:
   ```json
   {
     "scripts": {
       "electron:dev": "concurrently \"npm run client:dev\" \"wait-on http://localhost:5173 && electron .\"",
       "electron:build": "npm run client:build && electron-builder",
       "electron:build:win": "electron-builder --win",
       "electron:build:mac": "electron-builder --mac",
       "electron:build:linux": "electron-builder --linux"
     }
   }
   ```

#### Task 1.1.4: Create Electron Builder Configuration
**File**: `electron-builder.config.js` (NEW)

**Lines**: 1-150

**Subtasks**:
1. **Line 1-50**: Base configuration
   ```javascript
   module.exports = {
     appId: 'com.creditnexus.app',
     productName: 'CreditNexus',
     directories: {
       output: 'dist-electron'
     },
     files: [
       'electron/**/*',
       'client/dist/**/*',
       'app/**/*',
       'server.py',
       'requirements.txt',
       'package.json'
     ],
     win: {
       target: ['nsis', 'portable'],
       icon: 'assets/icon.ico'
     },
     mac: {
       target: ['dmg', 'zip'],
       icon: 'assets/icon.icns',
       category: 'public.app-category.finance'
     },
     linux: {
       target: ['AppImage', 'deb'],
       icon: 'assets/icon.png',
       category: 'Finance'
     },
     nsis: {
       oneClick: false,
       allowToChangeInstallationDirectory: true
     }
   };
   ```

### Activity 1.2: CI/CD Pipeline for Electron Builds

**File**: `.github/workflows/build-electron.yml` (NEW)

#### Task 1.2.1: Create GitHub Actions Workflow
**Lines**: 1-200

**Subtasks**:
1. **Line 1-50**: Workflow setup
   ```yaml
   name: Build Electron Application
   
   on:
     push:
       branches: [main, develop]
     pull_request:
       branches: [main]
     release:
       types: [created]
   
   jobs:
     build:
       runs-on: ${{ matrix.os }}
       strategy:
         matrix:
           os: [windows-latest, macos-latest, ubuntu-latest]
       
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: '20'
         - uses: actions/setup-python@v5
           with:
             python-version: '3.11'
   ```

2. **Line 51-100**: Build steps
   ```yaml
         - name: Install dependencies
           run: |
             npm install
             cd client && npm install
             pip install -r requirements.txt
       
         - name: Build frontend
           run: |
             cd client
             npm run build
       
         - name: Build Electron app
           run: npm run electron:build
           env:
             GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
       
         - name: Upload artifacts
           uses: actions/upload-artifact@v4
           with:
             name: creditnexus-${{ matrix.os }}
             path: dist-electron/**
   ```

---

## Project 2: Unified Dashboard Implementation

### Activity 2.1: Single Dashboard Component

**File**: `client/src/components/UnifiedDashboard.tsx` (NEW)

#### Task 2.1.1: Create Unified Dashboard Structure
**Lines**: 1-300

**Subtasks**:
1. **Line 1-100**: Component setup and state
   ```typescript
   import { useState, useEffect, useMemo } from 'react';
   import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
   import { usePermissions } from '@/hooks/usePermissions';
   import { useAuth } from '@/context/AuthContext';
   
   interface DashboardTab {
     id: string;
     label: string;
     icon: React.ReactNode;
     component: React.ComponentType;
     requiredPermission?: string;
     requiredPermissions?: string[];
     requireAll?: boolean;
     subscriptionTier?: 'free' | 'pro' | 'premium' | 'lifetime';
   }
   
   export function UnifiedDashboard() {
     const { user } = useAuth();
     const { hasPermission, hasPermissions } = usePermissions();
     const [activeTab, setActiveTab] = useState<string>('overview');
     
     // Get user subscription tier (from user model or API)
     const subscriptionTier = user?.subscription_tier || 'free';
   ```

2. **Line 101-200**: Tab configuration with permissions
   ```typescript
     const dashboardTabs: DashboardTab[] = useMemo(() => {
       const tabs: DashboardTab[] = [
         {
           id: 'overview',
           label: 'Overview',
           icon: <LayoutDashboard />,
           component: OverviewTab,
           subscriptionTier: 'free'
         },
         {
           id: 'trading',
           label: 'Trading',
           icon: <TrendingUp />,
           component: TradingDashboard,
           requiredPermission: PERMISSION_TRADING_VIEW,
           subscriptionTier: 'pro'
         },
         {
           id: 'polymarket',
           label: 'Polymarket',
           icon: <BarChart3 />,
           component: MarketDashboard,
           requiredPermission: PERMISSION_MARKET_VIEW,
           subscriptionTier: 'pro'
         },
         {
           id: 'documents',
           label: 'Documents',
           icon: <FileText />,
           component: DocumentHistory,
           requiredPermission: PERMISSION_DOCUMENT_VIEW,
           subscriptionTier: 'free'
         },
         {
           id: 'signatures',
           label: 'Signatures',
           icon: <PenTool />,
           component: SignatureDashboard,
           requiredPermission: PERMISSION_SIGNATURE_VIEW,
           subscriptionTier: 'free'
         },
         {
           id: 'compliance',
           label: 'Compliance',
           icon: <Shield />,
           component: ComplianceDashboard,
           requiredPermission: PERMISSION_COMPLIANCE_VIEW,
           subscriptionTier: 'premium'
         },
         {
           id: 'portfolio',
           label: 'Portfolio',
           icon: <PieChart />,
           component: PortfolioDashboard,
           requiredPermission: PERMISSION_PORTFOLIO_VIEW,
           subscriptionTier: 'pro'
         },
         {
           id: 'applications',
           label: 'Applications',
           icon: <FileCheck />,
           component: ApplicationDashboard,
           requiredPermission: PERMISSION_APPLICATION_VIEW,
           subscriptionTier: 'free'
         },
         {
           id: 'billing',
           label: 'Billing',
           icon: <DollarSign />,
           component: BillingDashboard,
           requiredPermission: PERMISSION_BILLING_VIEW,
           subscriptionTier: 'free'  // All tiers can view their billing
         }
       ];
       
       // Filter tabs based on permissions and subscription
       return tabs.filter(tab => {
         // Check subscription tier
         const tierLevels = { free: 0, pro: 1, premium: 2, lifetime: 3 };
         if (tierLevels[subscriptionTier] < tierLevels[tab.subscriptionTier || 'free']) {
           return false;
         }
         
         // Check permissions
         if (tab.requiredPermission) {
           if (!hasPermission(tab.requiredPermission)) {
             return false;
           }
         }
         if (tab.requiredPermissions) {
           if (!hasPermissions(tab.requiredPermissions, tab.requireAll)) {
             return false;
           }
         }
         
         return true;
       });
     }, [user, subscriptionTier, hasPermission, hasPermissions]);
   ```

3. **Line 201-300**: Render tabs
   ```typescript
     return (
       <div className="flex flex-col h-full">
         <Tabs value={activeTab} onValueChange={setActiveTab}>
           <TabsList className="w-full justify-start border-b">
             {dashboardTabs.map(tab => (
               <TabsTrigger
                 key={tab.id}
                 value={tab.id}
                 className="flex items-center gap-2"
               >
                 {tab.icon}
                 {tab.label}
               </TabsTrigger>
             ))}
           </TabsList>
           
           {dashboardTabs.map(tab => {
             const TabComponent = tab.component;
             return (
               <TabsContent key={tab.id} value={tab.id} className="flex-1 overflow-auto">
                 <TabComponent />
               </TabsContent>
             );
           })}
         </Tabs>
       </div>
     );
   }
   ```

### Activity 2.2: Update DesktopAppLayout

**File**: `client/src/components/DesktopAppLayout.tsx` (UPDATE)

#### Task 2.2.1: Replace Multiple Views with Unified Dashboard
**Lines**: ~986-1125 (replace app view rendering)

**Subtasks**:
1. Replace conditional rendering with UnifiedDashboard:
   ```typescript
   import { UnifiedDashboard } from '@/components/UnifiedDashboard';
   
   // In render section:
   {activeApp === 'dashboard' && <UnifiedDashboard />}
   ```

---

## Project 3: Enhanced Authentication with Verified Implementations

### Activity 3.1: Verified Implementations System

**File**: `app/db/models.py` (UPDATE)

#### Task 3.1.1: Add VerifiedImplementation Model
**Lines**: ~3000-3100 (after existing models)

**Subtasks**:
1. **Line 3000-3050**: Model definition
   ```python
   class VerifiedImplementation(Base):
       """Verified implementation provider (e.g., Alpaca, Plaid, Polymarket)."""
       __tablename__ = "verified_implementations"
       
       id = Column(Integer, primary_key=True)
       name = Column(String(100), unique=True, nullable=False)  # "alpaca", "plaid", "polymarket"
       display_name = Column(String(255), nullable=False)
       category = Column(String(50), nullable=False)  # "trading", "banking", "market", "payment"
       api_key_encrypted = Column(EncryptedString(500), nullable=True)
       api_secret_encrypted = Column(EncryptedString(500), nullable=True)
       base_url = Column(String(500), nullable=True)
       is_active = Column(Boolean, default=True, nullable=False)
       configuration = Column(JSONB, nullable=True)  # Provider-specific config
       created_at = Column(DateTime, default=datetime.utcnow)
       
       user_connections = relationship("UserImplementationConnection", back_populates="implementation")
   
   class UserImplementationConnection(Base):
       """User's connection to a verified implementation."""
       __tablename__ = "user_implementation_connections"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       implementation_id = Column(Integer, ForeignKey("verified_implementations.id"), nullable=False)
       connection_data = Column(EncryptedJSON(), nullable=True)  # OAuth tokens, API keys, etc.
       is_active = Column(Boolean, default=True, nullable=False)
       last_synced_at = Column(DateTime, nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow)
       
       user = relationship("User", back_populates="implementation_connections")
       implementation = relationship("VerifiedImplementation", back_populates="user_connections")
   ```

2. **Line 3051-3100**: Update User model
   ```python
   # In User model, add:
   implementation_connections = relationship("UserImplementationConnection", back_populates="user")
   selected_implementations = Column(JSONB, nullable=True)  # Array of implementation IDs user selected
   ```

#### Task 3.1.2: Update Login/Signup Forms

**File**: `client/src/components/LoginForm.tsx` (UPDATE)

**Lines**: ~40-100 (add implementation selection)

**Subtasks**:
1. **Line 40-60**: Add implementation selection state
   ```typescript
   const [selectedImplementations, setSelectedImplementations] = useState<string[]>([]);
   const [availableImplementations, setAvailableImplementations] = useState<Implementation[]>([]);
   
   useEffect(() => {
     // Fetch available implementations
     fetch('/api/implementations/available')
       .then(res => res.json())
       .then(data => setAvailableImplementations(data.implementations || []));
   }, []);
   ```

2. **Line 61-100**: Add implementation selector UI
   ```typescript
   <div className="space-y-2">
     <label className="text-sm font-medium">Verified Implementations (Optional)</label>
     <div className="grid grid-cols-2 gap-2">
       {availableImplementations.map(impl => (
         <label key={impl.id} className="flex items-center space-x-2 cursor-pointer">
           <input
             type="checkbox"
             checked={selectedImplementations.includes(impl.id)}
             onChange={(e) => {
               if (e.target.checked) {
                 setSelectedImplementations([...selectedImplementations, impl.id]);
               } else {
                 setSelectedImplementations(selectedImplementations.filter(id => id !== impl.id));
               }
             }}
           />
           <span>{impl.display_name}</span>
         </label>
       ))}
     </div>
   </div>
   ```

3. **Line 101-120**: Include in registration
   ```typescript
   const success = await register({
     email,
     password,
     display_name: displayName,
     selected_implementations: selectedImplementations
   });
   ```

#### Task 3.1.3: Backend API for Implementations

**File**: `app/api/implementation_routes.py` (NEW)

**Lines**: 1-200

**Subtasks**:
1. **Line 1-100**: List available implementations
   ```python
   @router.get("/implementations/available")
   async def list_available_implementations(
       db: Session = Depends(get_db)
   ):
       """List all available verified implementations."""
       implementations = db.query(VerifiedImplementation).filter(
           VerifiedImplementation.is_active == True
       ).all()
       
       return {
           "implementations": [
               {
                   "id": impl.id,
                   "name": impl.name,
                   "display_name": impl.display_name,
                   "category": impl.category
               }
               for impl in implementations
           ]
       }
   ```

2. **Line 101-200**: Connect user implementation
   ```python
   @router.post("/implementations/{impl_id}/connect")
   async def connect_implementation(
       impl_id: int,
       connection_data: Dict[str, Any],
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       """Connect user to a verified implementation."""
       implementation = db.query(VerifiedImplementation).filter(
           VerifiedImplementation.id == impl_id
       ).first()
       
       if not implementation:
           raise HTTPException(404, "Implementation not found")
       
       # Create or update connection
       connection = db.query(UserImplementationConnection).filter(
           UserImplementationConnection.user_id == current_user.id,
           UserImplementationConnection.implementation_id == impl_id
       ).first()
       
       if connection:
           connection.connection_data = connection_data
           connection.is_active = True
       else:
           connection = UserImplementationConnection(
               user_id=current_user.id,
               implementation_id=impl_id,
               connection_data=connection_data,
               is_active=True
           )
           db.add(connection)
       
       db.commit()
       return {"status": "connected", "connection_id": connection.id}
   ```

---

## Project 4: Subscription & Payment System

### Activity 4.1: Subscription Models

**File**: `app/db/models.py` (UPDATE)

#### Task 4.1.1: Add Subscription Models
**Lines**: ~3100-3250

**Subtasks**:
1. **Line 3100-3180**: Subscription models
   ```python
   class SubscriptionTier(str, enum.Enum):
       FREE = "free"
       PRO = "pro"
       PREMIUM = "premium"
       LIFETIME = "lifetime"
   
   class SubscriptionType(str, enum.Enum):
       PAY_AS_YOU_GO = "pay_as_you_go"  # Pro tier
       MONTHLY = "monthly"
       YEARLY = "yearly"
       LIFETIME = "lifetime"
   
   class UserSubscription(Base):
       """User subscription record."""
       __tablename__ = "user_subscriptions"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       tier = Column(String(20), nullable=False)  # SubscriptionTier enum
       subscription_type = Column(String(20), nullable=False)  # SubscriptionType enum
       is_active = Column(Boolean, default=True, nullable=False)
       started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       expires_at = Column(DateTime, nullable=True)  # NULL for lifetime
       payment_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
       auto_renew = Column(Boolean, default=False, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow)
       
       user = relationship("User", back_populates="subscriptions")
       payment = relationship("PaymentEvent", foreign_keys=[payment_id])
   
   class SubscriptionUsage(Base):
       """Pay-as-you-go usage tracking for Pro tier."""
       __tablename__ = "subscription_usage"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False)
       feature = Column(String(50), nullable=False)  # "trade_execution", "market_creation", etc.
       usage_count = Column(Integer, default=0, nullable=False)
       billing_period_start = Column(DateTime, nullable=False)
       billing_period_end = Column(DateTime, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow)
       
       user = relationship("User")
       subscription = relationship("UserSubscription")
   ```

2. **Line 3181-3250**: Update User model
   ```python
   # In User model, add:
   subscriptions = relationship("UserSubscription", back_populates="user")
   subscription_tier = Column(String(20), default=SubscriptionTier.FREE.value, nullable=False)
   ```

#### Task 4.1.2: Subscription Service

**File**: `app/services/subscription_service.py` (NEW)

**Lines**: 1-300

**Subtasks**:
1. **Line 1-100**: Service class and initialization
   ```python
   class SubscriptionService:
       """Service for managing user subscriptions."""
       
       def __init__(self, db: Session):
           self.db = db
       
       def get_user_tier(self, user_id: int) -> str:
           """Get user's current subscription tier."""
           user = self.db.query(User).filter(User.id == user_id).first()
           if not user:
               return SubscriptionTier.FREE.value
           
           # Check for active subscription
           active_sub = self.db.query(UserSubscription).filter(
               UserSubscription.user_id == user_id,
               UserSubscription.is_active == True
           ).first()
           
           if active_sub:
               # Check if expired (unless lifetime)
               if active_sub.expires_at and active_sub.expires_at < datetime.utcnow():
                   return SubscriptionTier.FREE.value
               return active_sub.tier
           
           return user.subscription_tier or SubscriptionTier.FREE.value
   ```

2. **Line 101-200**: Create subscription
   ```python
       def create_subscription(
           self,
           user_id: int,
           tier: str,
           subscription_type: str,
           payment_id: Optional[int] = None,
           lifetime: bool = False
       ) -> UserSubscription:
           """Create a new subscription."""
           if lifetime:
               expires_at = None
           elif subscription_type == SubscriptionType.MONTHLY.value:
               expires_at = datetime.utcnow() + timedelta(days=30)
           elif subscription_type == SubscriptionType.YEARLY.value:
               expires_at = datetime.utcnow() + timedelta(days=365)
           else:
               expires_at = None  # Pay-as-you-go
           
           subscription = UserSubscription(
               user_id=user_id,
               tier=tier,
               subscription_type=subscription_type,
               payment_id=payment_id,
               expires_at=expires_at,
               is_active=True
           )
           self.db.add(subscription)
           
           # Update user tier
           user = self.db.query(User).filter(User.id == user_id).first()
           if user:
               user.subscription_tier = tier
           
           self.db.commit()
           return subscription
   ```

3. **Line 201-300**: Usage tracking for pay-as-you-go
   ```python
       def track_usage(
           self,
           user_id: int,
           feature: str,
           increment: int = 1
       ) -> Dict[str, Any]:
           """Track usage for pay-as-you-go subscriptions."""
           tier = self.get_user_tier(user_id)
           if tier != SubscriptionTier.PRO.value:
               return {"tracked": False, "reason": "not_pro_tier"}
           
           # Get current billing period
           now = datetime.utcnow()
           period_start = datetime(now.year, now.month, 1)
           period_end = period_start + timedelta(days=32)
           period_end = period_end.replace(day=1) - timedelta(days=1)
           
           usage = self.db.query(SubscriptionUsage).filter(
               SubscriptionUsage.user_id == user_id,
               SubscriptionUsage.feature == feature,
               SubscriptionUsage.billing_period_start == period_start
           ).first()
           
           if usage:
               usage.usage_count += increment
           else:
               subscription = self.db.query(UserSubscription).filter(
                   UserSubscription.user_id == user_id,
                   UserSubscription.is_active == True
               ).first()
               
               usage = SubscriptionUsage(
                   user_id=user_id,
                   subscription_id=subscription.id if subscription else None,
                   feature=feature,
                   usage_count=increment,
                   billing_period_start=period_start,
                   billing_period_end=period_end
               )
               self.db.add(usage)
           
           self.db.commit()
           return {"tracked": True, "usage_count": usage.usage_count}
   ```

---

## Project 5: Commission & Fee Configuration System

### Activity 5.1: Commission Configuration Models

**File**: `app/db/models.py` (UPDATE)

#### Task 5.1.1: Add Commission Models
**Lines**: ~3250-3400

**Subtasks**:
1. **Line 3250-3350**: Commission configuration model
   ```python
   class CommissionConfig(Base):
       """Configurable commission and fee structure."""
       __tablename__ = "commission_configs"
       
       id = Column(Integer, primary_key=True)
       name = Column(String(100), nullable=False)  # "trade_execution", "market_creation", "deal_processing"
       category = Column(String(50), nullable=False)  # "trading", "market", "deal", "payment"
       fee_type = Column(String(20), nullable=False)  # "percentage", "fixed", "tiered"
       fee_value = Column(Numeric(10, 4), nullable=False)  # Percentage (0.01 = 1%) or fixed amount
       min_fee = Column(Numeric(19, 4), nullable=True)
       max_fee = Column(Numeric(19, 4), nullable=True)
       currency = Column(String(3), default="USD", nullable=False)
       applies_to = Column(JSONB, nullable=True)  # Conditions: deal_type, workflow_type, etc.
       is_active = Column(Boolean, default=True, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   
   class CommissionCharge(Base):
       """Record of commission charges applied."""
       __tablename__ = "commission_charges"
       
       id = Column(Integer, primary_key=True)
       config_id = Column(Integer, ForeignKey("commission_configs.id"), nullable=False)
       transaction_id = Column(String(255), nullable=False, index=True)  # Deal ID, Trade ID, etc.
       transaction_type = Column(String(50), nullable=False)  # "trade", "deal", "market", etc.
       amount = Column(Numeric(19, 4), nullable=False)
       currency = Column(String(3), nullable=False)
       payer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
       calculation_details = Column(JSONB, nullable=True)  # How fee was calculated
       payment_event_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow)
       
       config = relationship("CommissionConfig")
       payer = relationship("User")
       payment_event = relationship("PaymentEvent")
   ```

#### Task 5.1.2: Commission Calculation Service

**File**: `app/services/commission_service.py` (NEW)

**Lines**: 1-250

**Subtasks**:
1. **Line 1-100**: Service class
   ```python
   class CommissionService:
       """Service for calculating and applying commissions."""
       
       def __init__(self, db: Session):
           self.db = db
       
       def calculate_commission(
           self,
           transaction_type: str,
           transaction_amount: Decimal,
           transaction_metadata: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Calculate commission for a transaction."""
           # Find applicable commission config
           config = self.db.query(CommissionConfig).filter(
               CommissionConfig.category == transaction_type,
               CommissionConfig.is_active == True
           ).first()
           
           if not config:
               return {"commission": Decimal("0"), "config_id": None}
           
           # Calculate based on fee type
           if config.fee_type == "percentage":
               commission = transaction_amount * (config.fee_value / 100)
           elif config.fee_type == "fixed":
               commission = config.fee_value
           else:  # tiered
               commission = self._calculate_tiered_fee(config, transaction_amount)
           
           # Apply min/max limits
           if config.min_fee:
               commission = max(commission, config.min_fee)
           if config.max_fee:
               commission = min(commission, config.max_fee)
           
           return {
               "commission": commission,
               "config_id": config.id,
               "fee_type": config.fee_type,
               "currency": config.currency
           }
   ```

2. **Line 101-200**: Apply commission
   ```python
       def apply_commission(
           self,
           transaction_id: str,
           transaction_type: str,
           transaction_amount: Decimal,
           payer_id: int,
           transaction_metadata: Dict[str, Any]
       ) -> CommissionCharge:
           """Apply commission to a transaction."""
           calculation = self.calculate_commission(
               transaction_type,
               transaction_amount,
               transaction_metadata
           )
           
           charge = CommissionCharge(
               config_id=calculation["config_id"],
               transaction_id=transaction_id,
               transaction_type=transaction_type,
               amount=calculation["commission"],
               currency=calculation["currency"],
               payer_id=payer_id,
               calculation_details=calculation
           )
           self.db.add(charge)
           self.db.commit()
           
           return charge
   ```

---

## Project 6: New Roles & Permissions

### Activity 6.1: Add Trader and Compliance Officer Roles

**File**: `app/db/models.py` (UPDATE)

#### Task 6.1.1: Update UserRole Enum
**Lines**: ~14-28 (update existing enum)

**Subtasks**:
1. Add new roles:
   ```python
   class UserRole(str, enum.Enum):
       # Existing roles
       AUDITOR = "auditor"
       BANKER = "banker"
       LAW_OFFICER = "law_officer"
       ACCOUNTANT = "accountant"
       APPLICANT = "applicant"
       VIEWER = "viewer"
       ANALYST = "analyst"
       REVIEWER = "reviewer"
       ADMIN = "admin"
       # New roles
       TRADER = "trader"  # Trading and portfolio management
       COMPLIANCE_OFFICER = "compliance_officer"  # Compliance monitoring and reporting
   ```

#### Task 6.1.2: Update Permissions

**File**: `app/core/permissions.py` (UPDATE)

**Lines**: ~100-150 (add new permissions)

**Subtasks**:
1. Add new permission constants:
   ```python
   # Trading Permissions
   PERMISSION_TRADING_VIEW = "TRADING_VIEW"
   PERMISSION_TRADING_TRADE = "TRADING_TRADE"
   PERMISSION_TRADING_ADVANCED_ORDERS = "TRADING_ADVANCED_ORDERS"
   PERMISSION_TRADING_MARKET_DATA = "TRADING_MARKET_DATA"
   
   # Compliance Permissions
   PERMISSION_COMPLIANCE_VIEW = "COMPLIANCE_VIEW"
   PERMISSION_COMPLIANCE_AUDIT = "COMPLIANCE_AUDIT"
   PERMISSION_COMPLIANCE_REPORT = "COMPLIANCE_REPORT"
   PERMISSION_COMPLIANCE_APPROVE = "COMPLIANCE_APPROVE"
   
   # Portfolio Permissions
   PERMISSION_PORTFOLIO_VIEW = "PORTFOLIO_VIEW"
   PERMISSION_PORTFOLIO_MANAGE = "PORTFOLIO_MANAGE"
   
   # Market Permissions (from Polymarket plan)
   PERMISSION_MARKET_CREATE = "MARKET_CREATE"
   PERMISSION_MARKET_VIEW = "MARKET_VIEW"
   PERMISSION_MARKET_TRADE = "MARKET_TRADE"
   PERMISSION_MARKET_RESOLVE = "MARKET_RESOLVE"
   
   # Signature Permissions (from DigiSign plan)
   PERMISSION_SIGNATURE_COORDINATE = "SIGNATURE_COORDINATE"
   PERMISSION_SIGNATURE_EXECUTE = "SIGNATURE_EXECUTE"
   PERMISSION_SIGNATURE_AUDIT = "SIGNATURE_AUDIT"
   PERMISSION_SIGNATURE_VIEW = "SIGNATURE_VIEW"
   
   # Billing Permissions (from Billing Dashboard plan)
   PERMISSION_BILLING_VIEW = "BILLING_VIEW"
   PERMISSION_BILLING_VIEW_ALL = "BILLING_VIEW_ALL"  # Admin only
   PERMISSION_BILLING_VIEW_ORGANIZATION = "BILLING_VIEW_ORGANIZATION"  # Org admin
   ```

2. **Line 350-450**: Add role permissions
   ```python
   ROLE_PERMISSIONS = {
       # ... existing roles ...
       
       UserRole.TRADER.value: [
           PERMISSION_TRADING_VIEW,
           PERMISSION_TRADING_TRADE,
           PERMISSION_TRADING_MARKET_DATA,
           PERMISSION_PORTFOLIO_VIEW,
           PERMISSION_PORTFOLIO_MANAGE,
           PERMISSION_MARKET_VIEW,
           PERMISSION_MARKET_TRADE,
           PERMISSION_DOCUMENT_VIEW,
           PERMISSION_DEAL_VIEW,
       ],
       
       UserRole.COMPLIANCE_OFFICER.value: [
           PERMISSION_COMPLIANCE_VIEW,
           PERMISSION_COMPLIANCE_AUDIT,
           PERMISSION_COMPLIANCE_REPORT,
           PERMISSION_COMPLIANCE_APPROVE,
           PERMISSION_DOCUMENT_VIEW,
           PERMISSION_DEAL_VIEW,
           PERMISSION_TRADE_VIEW,
           PERMISSION_AUDIT_VIEW,
           PERMISSION_POLICY_VIEW,
           PERMISSION_SIGNATURE_AUDIT,
       ],
       
       UserRole.ADMIN.value: [
           # ... existing admin permissions ...
           PERMISSION_BILLING_VIEW,
           PERMISSION_BILLING_VIEW_ALL,
           PERMISSION_BILLING_VIEW_ORGANIZATION,
       ],
   }
   ```

---

## Project 7: Setup Scripts

### Activity 7.1: Cross-Platform Setup Scripts

**File**: `scripts/setup.sh` (NEW)

#### Task 7.1.1: Create Bash Setup Script
**Lines**: 1-200

**Subtasks**:
1. **Line 1-50**: Script header and checks
   ```bash
   #!/bin/bash
   set -e
   
   echo "CreditNexus Setup Script"
   echo "========================"
   echo ""
   
   # Check Python version
   if ! command -v python3 &> /dev/null; then
       echo "Error: Python 3.11+ is required"
       exit 1
   fi
   
   PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
   if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
       echo "Error: Python 3.11+ is required (found $PYTHON_VERSION)"
       exit 1
   fi
   ```

2. **Line 51-100**: Environment setup
   ```bash
   # Create virtual environment
   if [ ! -d "venv" ]; then
       echo "Creating Python virtual environment..."
       python3 -m venv venv
   fi
   
   source venv/bin/activate
   
   # Install Python dependencies
   echo "Installing Python dependencies..."
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Line 101-150**: Node.js setup
   ```bash
   # Check Node.js
   if ! command -v node &> /dev/null; then
       echo "Error: Node.js 20+ is required"
       exit 1
   fi
   
   # Install frontend dependencies
   echo "Installing frontend dependencies..."
   cd client
   npm install
   cd ..
   ```

4. **Line 151-200**: Database and configuration
   ```bash
   # Setup .env file
   if [ ! -f ".env" ]; then
       echo "Creating .env file from template..."
       cp .env.example .env
       echo ""
       echo "Please edit .env file with your configuration"
   fi
   
   # Initialize database
   echo "Initializing database..."
   alembic upgrade head
   
   echo ""
   echo "Setup complete!"
   echo "To start the application:"
   echo "  source venv/bin/activate"
   echo "  python server.py"
   echo ""
   echo "In another terminal:"
   echo "  cd client && npm run dev"
   ```

#### Task 7.1.2: Create PowerShell Setup Script

**File**: `scripts/setup.ps1` (NEW)

**Lines**: 1-250

**Subtasks**:
1. Similar structure to bash script but PowerShell syntax
2. Check for Python, Node.js
3. Create venv, install dependencies
4. Setup .env file
5. Initialize database

---

## Project 8: Integration of Feature Plans

### Activity 8.1: Polymarket Integration Updates

**Update**: `dev/POLYMARKET_INTEGRATION_PLAN.md`

#### Task 8.1.1: Add Unified Dashboard Integration
- Update MarketDashboard to be a tab in UnifiedDashboard
- Add permission checks for market features
- Integrate with subscription tier system

### Activity 8.2: Trading Dashboard Integration Updates

**Update**: `dev/TRADING_DASHBOARD_IMPLEMENTATION_PLAN.md`

#### Task 8.2.1: Add Unified Dashboard Integration
- Update TradingDashboard to be a tab in UnifiedDashboard
- Add permission checks for trading features
- Integrate with subscription tier system
- Add commission calculation for trades

### Activity 8.3: DigiSign Integration Updates

**Update**: `dev/DIGISIGN_IMPLEMENTATION_PLAN.md`

#### Task 8.3.1: Add Unified Dashboard Integration
- Update SignatureDashboard to be a tab in UnifiedDashboard
- Add permission checks for signature features
- Integrate with subscription tier system

---

## Project 9: FDC3 & OpenFin Compatibility

### Activity 9.1: Electron FDC3 Bridge

**File**: `electron/fdc3-bridge.js` (NEW)

#### Task 9.1.1: Create FDC3 Bridge for Electron
**Lines**: 1-150

**Subtasks**:
1. Bridge FDC3 API calls between Electron and renderer
2. Support both FDC3 2.0 and OpenFin APIs
3. Handle context broadcasting
4. Support intent handling

---

## Implementation Checklist

### Phase 1: Electron Setup (Weeks 1-2)
- [ ] **Week 1**: Electron main process and preload script
- [ ] **Week 2**: Build configuration and CI/CD pipeline

### Phase 2: Unified Dashboard (Weeks 3-4)
- [ ] **Week 3**: UnifiedDashboard component with tab system
- [ ] **Week 4**: Permission-based tab filtering and subscription tier checks

### Phase 3: Enhanced Authentication (Weeks 5-6)
- [ ] **Week 5**: Verified implementations system (models, API)
- [ ] **Week 6**: Login/signup UI updates with implementation selection

### Phase 4: Subscription System (Weeks 7-8)
- [ ] **Week 7**: Subscription models and service
- [ ] **Week 8**: Pay-as-you-go usage tracking and lifetime payments

### Phase 5: Commission System (Weeks 9-10)
- [ ] **Week 9**: Commission configuration models and service
- [ ] **Week 10**: Commission calculation and application

### Phase 6: New Roles & Permissions (Week 11)
- [ ] **Week 11**: Trader and Compliance Officer roles, permission updates

### Phase 7: Setup Scripts (Week 12)
- [ ] **Week 12**: Cross-platform setup scripts (bash and PowerShell)

### Phase 8: Feature Integration (Weeks 13-15)
- [ ] **Week 13**: Polymarket integration into unified dashboard
- [ ] **Week 14**: Trading dashboard integration
- [ ] **Week 15**: DigiSign integration

### Phase 9: FDC3/OpenFin (Week 16)
- [ ] **Week 16**: FDC3 bridge for Electron and OpenFin compatibility

### Phase 10: Testing & Documentation (Weeks 17-18)
- [ ] **Week 17**: End-to-end testing
- [ ] **Week 18**: Documentation and deployment guides

---

## Success Criteria

1. ✅ Electron app builds to .exe, .dmg, and .AppImage
2. ✅ CI/CD pipeline automatically builds on push/release
3. ✅ Unified dashboard shows only permissioned tabs
4. ✅ Subscription tiers properly gate features
5. ✅ Verified implementations can be selected during signup
6. ✅ Commissions are calculated and applied automatically
7. ✅ Setup scripts work on Windows, macOS, and Linux
8. ✅ FDC3 and OpenFin interoperability maintained
9. ✅ All three feature plans (Polymarket, Trading, DigiSign) integrated
10. ✅ New roles (Trader, Compliance Officer) have appropriate permissions

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
