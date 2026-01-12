"""
Demo Data Seeding Service for CreditNexus.

This service provides a unified interface for seeding demo data including:
- Users (via existing seed scripts)
- Templates (via existing seed scripts)
- Policies (via existing seed scripts)
- AI-generated deals with complete data flow
- Documents, workflows, and related entities
"""

import logging
import random
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import (
    User, UserRole, Deal, Application, Document, DocumentVersion, Workflow,
    GeneratedDocument, DealNote, PolicyDecision, DealStatus,
    DealType, ApplicationStatus, ApplicationType, WorkflowState, GeneratedDocumentStatus,
    GreenFinanceAssessment
)
from app.models.cdm import CreditAgreement
from app.models.loan_asset import LoanAsset

logger = logging.getLogger(__name__)


@dataclass
class SeedingStatus:
    """Status tracking for seeding operations."""
    stage: str  # users, templates, deals, documents, etc.
    progress: float = 0.0  # 0.0 to 1.0
    total: int = 0
    current: int = 0
    errors: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Global seeding status store - persists across requests
# This is necessary because each API request creates a new DemoDataService instance
_global_seeding_status: Dict[str, SeedingStatus] = {}


class DemoDataService:
    """Service for seeding and managing demo data."""
    
    def __init__(self, db: Session):
        """
        Initialize demo data service.
        
        Args:
            db: Database session
        """
        self.db = db
        # Use global status store to persist status across requests
        self._status = _global_seeding_status
        self._progress_callback: Optional[Callable[[str, SeedingStatus], None]] = None
    
    def set_progress_callback(self, callback: Callable[[str, SeedingStatus], None]):
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def _update_status(self, stage: str, **kwargs):
        """Update status for a stage."""
        if stage not in self._status:
            self._status[stage] = SeedingStatus(stage=stage)
        
        status = self._status[stage]
        for key, value in kwargs.items():
            if hasattr(status, key):
                setattr(status, key, value)
        
        if self._progress_callback:
            self._progress_callback(stage, status)
    
    def seed_all(
        self,
        seed_users: bool = True,
        seed_templates: bool = True,
        seed_policies: bool = True,
        seed_policy_templates: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Seed all demo data.
        
        Args:
            seed_users: Whether to seed users
            seed_templates: Whether to seed templates
            seed_policies: Whether to seed policies
            seed_policy_templates: Whether to seed policy templates
            dry_run: If True, preview what would be seeded without committing
            
        Returns:
            Dictionary with seeding results
        """
        results = {
            "users": {"created": 0, "updated": 0, "errors": []},
            "templates": {"created": 0, "updated": 0, "errors": []},
            "policies": {"created": 0, "updated": 0, "errors": []},
            "policy_templates": {"created": 0, "updated": 0, "errors": []},
        }
        
        try:
            if seed_users:
                results["users"] = self.seed_users(dry_run=dry_run)
            
            if seed_templates:
                results["templates"] = self.seed_templates(dry_run=dry_run)
            
            if seed_policies:
                results["policies"] = self.seed_policies(dry_run=dry_run)
            
            if seed_policy_templates:
                results["policy_templates"] = self.seed_policy_templates(dry_run=dry_run)
            
            if not dry_run:
                self.db.commit()
            
            return results
        except Exception as e:
            logger.error(f"Error seeding demo data: {e}", exc_info=True)
            if not dry_run:
                self.db.rollback()
            raise
    
    def seed_users(self, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Seed demo users.
        
        Args:
            force: If True, update existing users
            dry_run: If True, preview without committing
            
        Returns:
            Dictionary with created/updated counts, errors, and user credentials
        """
        self._update_status("users", status="running", started_at=datetime.utcnow())
        
        try:
            # Import seed function and user definitions
            from scripts.seed_demo_users import seed_demo_users, DEMO_USERS
            
            # Call seed function with seed_all_roles=True to ensure all users are created
            # (API calls should seed all roles by default, not rely on environment variables)
            count = seed_demo_users(self.db, force=force, seed_all_roles=True)
            
            # Prepare user credentials list
            user_credentials = []
            for user_data in DEMO_USERS:
                user_credentials.append({
                    "email": user_data["email"],
                    "password": user_data["password"],
                    "role": user_data["role"].value,
                    "display_name": user_data["display_name"]
                })
            
            result = {
                "created": count if not force else 0,
                "updated": count if force else 0,
                "errors": [],
                "user_credentials": user_credentials
            }
            
            self._update_status("users", status="completed", completed_at=datetime.utcnow(), current=count, total=count, progress=1.0)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error seeding users: {error_msg}", exc_info=True)
            self._update_status("users", status="failed", completed_at=datetime.utcnow(), errors=[error_msg])
            return {"created": 0, "updated": 0, "errors": [error_msg], "user_credentials": []}
    
    def seed_templates(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Seed templates.
        
        Args:
            dry_run: If True, preview without committing
            
        Returns:
            Dictionary with created/updated counts and errors
        """
        self._update_status("templates", status="running", started_at=datetime.utcnow())
        
        try:
            # Import seed function
            from scripts.seed_templates import seed_templates
            import json
            from pathlib import Path
            
            # Load templates metadata
            templates_file = Path("data/templates_metadata.json")
            if not templates_file.exists():
                raise FileNotFoundError(f"Templates metadata file not found: {templates_file}")
            
            with open(templates_file, "r", encoding="utf-8") as f:
                templates_data = json.load(f)
            
            # Call seed function
            count = seed_templates(self.db, templates_data)
            
            result = {
                "created": count,
                "updated": 0,
                "errors": []
            }
            
            self._update_status("templates", status="completed", completed_at=datetime.utcnow(), current=count, total=count, progress=1.0)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error seeding templates: {error_msg}", exc_info=True)
            self._update_status("templates", status="failed", completed_at=datetime.utcnow(), errors=[error_msg])
            return {"created": 0, "updated": 0, "errors": [error_msg]}
    
    def seed_policies(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Seed policies from YAML files.
        
        Args:
            dry_run: If True, preview without committing
            
        Returns:
            Dictionary with created/updated counts and errors
        """
        self._update_status("policies", status="running", started_at=datetime.utcnow())
        
        try:
            # Import seed function
            from scripts.seed_policies import seed_policies_from_yaml
            from app.db.models import User
            
            # Get admin user ID
            admin = self.db.query(User).filter(User.role == 'admin').first()
            admin_user_id = admin.id if admin else 1
            
            # Call seed function
            count = seed_policies_from_yaml(self.db, admin_user_id)
            
            result = {
                "created": count,
                "updated": 0,
                "errors": []
            }
            
            self._update_status("policies", status="completed", completed_at=datetime.utcnow(), current=count, total=count, progress=1.0)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error seeding policies: {error_msg}", exc_info=True)
            self._update_status("policies", status="failed", completed_at=datetime.utcnow(), errors=[error_msg])
            return {"created": 0, "updated": 0, "errors": [error_msg]}
    
    def seed_policy_templates(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Seed policy templates.
        
        Args:
            dry_run: If True, preview without committing
            
        Returns:
            Dictionary with created/updated counts and errors
        """
        self._update_status("policy_templates", status="running", started_at=datetime.utcnow())
        
        try:
            # Import seed function (if exists)
            try:
                from scripts.seed_policy_templates import seed_policy_templates
                count = seed_policy_templates(self.db)
            except ImportError:
                logger.warning("seed_policy_templates not available, skipping")
                count = 0
            
            result = {
                "created": count,
                "updated": 0,
                "errors": []
            }
            
            self._update_status("policy_templates", status="completed", completed_at=datetime.utcnow(), current=count, total=count, progress=1.0)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error seeding policy templates: {error_msg}", exc_info=True)
            self._update_status("policy_templates", status="failed", completed_at=datetime.utcnow(), errors=[error_msg])
            return {"created": 0, "updated": 0, "errors": [error_msg]}
    
    def get_seeding_status(self, stage: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current seeding status.
        
        Args:
            stage: Optional stage name to get status for specific stage
            
        Returns:
            Dictionary with status information
        """
        if stage:
            status = self._status.get(stage)
            if status:
                return {
                    "stage": status.stage,
                    "progress": status.progress,
                    "total": status.total,
                    "current": status.current,
                    "errors": status.errors,
                    "status": status.status,
                    "started_at": status.started_at.isoformat() if status.started_at else None,
                    "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                }
            return None
        
        # Return all statuses
        return {
            stage: {
                "stage": status.stage,
                "progress": status.progress,
                "total": status.total,
                "current": status.current,
                "errors": status.errors,
                "status": status.status,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "completed_at": status.completed_at.isoformat() if status.completed_at else None,
            }
            for stage, status in self._status.items()
        }
    
    def _generate_cdm_for_deal(
        self,
        deal_type: str,
        seed: Optional[int] = None,
        scenario: Optional[str] = None,
        use_cache: bool = True
    ) -> CreditAgreement:
        """
        Generate CDM data for a deal using AI with optional caching.
        
        Args:
            deal_type: Type of deal (loan_application, refinancing, restructuring)
            seed: Random seed for reproducibility
            scenario: Scenario template (if None, randomly selects)
            use_cache: Whether to use cache (default: True)
            
        Returns:
            CreditAgreement instance
        """
        # Check cache first if enabled
        if use_cache:
            try:
                from app.services.demo_data_cache import get_demo_cache
                cache = get_demo_cache()
                
                cached_cdm = cache.get_cached_deal(seed=seed or 0, deal_type=deal_type, scenario=scenario)
                if cached_cdm:
                    logger.debug(f"Cache hit for deal (seed={seed}, type={deal_type}, scenario={scenario})")
                    try:
                        return CreditAgreement(**cached_cdm.get("cdm", cached_cdm))
                    except Exception as e:
                        logger.warning(f"Failed to deserialize cached CDM: {e}")
                        # Fall through to generation
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")
                # Fall through to generation
        
        # Generate new CDM
        from app.chains.deal_generation_chain import generate_cdm_for_deal
        
        cdm = generate_cdm_for_deal(
            deal_type=deal_type,
            scenario=scenario,
            seed=seed
        )
        
        # Cache the result if enabled
        if use_cache:
            try:
                from app.services.demo_data_cache import get_demo_cache
                cache = get_demo_cache()
                
                cache.cache_deal(
                    seed=seed or 0,
                    deal_type=deal_type,
                    deal_data={"cdm": cdm.model_dump()},
                    scenario=scenario
                )
                logger.debug(f"Cached deal (seed={seed}, type={deal_type}, scenario={scenario})")
            except Exception as e:
                logger.warning(f"Failed to cache deal: {e}")
        
        return cdm
    
    def generate_deal_data(
        self,
        count: int = 12,
        deal_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate deal data using AI.
        
        Args:
            count: Number of deals to generate
            deal_types: List of deal types to generate (if None, uses defaults)
            
        Returns:
            List of deal data dictionaries
        """
        if deal_types is None:
            deal_types = ["loan_application", "refinancing", "restructuring"]
        
        deals = []
        self._update_status("deals", status="running", started_at=datetime.utcnow(), total=count, current=0)
        
        for i in range(count):
            try:
                # Select deal type
                deal_type = random.choice(deal_types) if deal_types else "loan_application"
                
                # Generate CDM
                cdm = self._generate_cdm_for_deal(deal_type=deal_type, seed=i)
                
                # Convert to dict
                deal_data = {
                    "cdm": cdm.model_dump(),
                    "deal_type": deal_type,
                    "seed": i
                }
                
                deals.append(deal_data)
                self._update_status("deals", current=i + 1, progress=(i + 1) / count)
                
            except Exception as e:
                error_msg = f"Failed to generate deal {i + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("deals", errors=[error_msg])
                continue
        
        self._update_status("deals", status="completed", completed_at=datetime.utcnow())
        return deals
    
    def create_demo_deals(self, count: int = 12) -> List[Deal]:
        """
        Create complete demo deals with full data flow: Applications → Deals → Documents → Workflows.
        
        Only creates new deals if the requested count exceeds existing demo deals.
        
        Args:
            count: Number of deals to have (not number to create)
            
        Returns:
            List of created Deal objects (empty if count satisfied by existing)
        """
        # Check existing demo deals
        existing_demo_deals = self.db.query(Deal).filter(Deal.is_demo == True).count()
        
        # If we already have enough demo deals, skip creation
        if existing_demo_deals >= count:
            logger.info(f"Skipping deal creation: {existing_demo_deals} demo deals exist, {count} requested")
            self._update_status("deals", status="completed", completed_at=datetime.utcnow(), 
                              total=count, current=count, progress=1.0)
            return []
        
        # Only create the difference
        deals_to_create = count - existing_demo_deals
        logger.info(f"Creating {deals_to_create} new demo deals (have {existing_demo_deals}, want {count})")
        
        self._update_status("deals", status="running", started_at=datetime.utcnow(), total=deals_to_create, current=0)
        
        # Step 1: Generate Applications
        applications = self._generate_applications(deals_to_create)
        
        # Step 2: Create Deals from Applications
        deals = self._create_deals_from_applications(applications)
        
        # Step 3: Generate Documents for Deals
        documents = self._generate_deal_documents(deals)
        
        # Step 4: Create DocumentVersions for Documents
        document_versions = self._create_document_versions(documents)
        
        # Step 4b: Create revision history for 30% of documents
        document_ids_for_revision = [d.id for d in documents]
        revision_versions = self.create_document_revision_history(document_ids_for_revision)
        document_versions.extend(revision_versions)
        
        # Step 5: Generate Workflows for Documents
        workflows = self._create_workflows_for_documents(documents)
        
        # Step 6: Generate LoanAssets for sustainability-linked deals
        loan_assets = self._generate_loan_assets_for_deals(deals)
        
        # Step 6b: Create green finance assessments for loan assets
        if loan_assets and settings.ENHANCED_SATELLITE_ENABLED:
            try:
                green_finance_assessments = self._create_green_finance_assessments(loan_assets, deals)
                logger.info(f"Created {len(green_finance_assessments)} green finance assessments for demo loan assets")
            except Exception as e:
                logger.warning(f"Failed to create green finance assessments: {e}")
        
        # Step 7: Generate documents from templates for approved deals
        approved_deals = [d for d in deals if d.status in [DealStatus.APPROVED.value, DealStatus.ACTIVE.value]]
        generated_docs = []
        for deal in approved_deals:
            try:
                docs = self.generate_documents_from_templates(deal.id)
                generated_docs.extend(docs)
            except Exception as e:
                logger.warning(f"Failed to generate documents from templates for deal {deal.id}: {e}")
        
        # Step 8: Create deal notes
        deal_notes = self.create_deal_notes([d.id for d in deals])
        
        # Step 9: Create policy decisions for documents
        policy_decisions = self.create_policy_decisions_for_documents([d.id for d in documents])
        
        # Step 9b: Create green finance policy decisions for loan assets (if enabled)
        if loan_assets and settings.ENHANCED_SATELLITE_ENABLED:
            try:
                green_policy_decisions = self._create_green_finance_policy_decisions(loan_assets, deals)
                policy_decisions.extend(green_policy_decisions)
                logger.info(f"Created {len(green_policy_decisions)} green finance policy decisions")
            except Exception as e:
                logger.warning(f"Failed to create green finance policy decisions: {e}")
        
        # Step 10: Store generated documents as files
        self._store_generated_documents(deals, documents, document_versions, generated_docs)
        
        # Step 11: Index documents in ChromaDB
        self.index_demo_documents([d.id for d in documents])
        
        self._update_status("deals", status="completed", completed_at=datetime.utcnow(), current=len(deals), progress=1.0)
        
        return deals
    
    def _generate_applications(self, count: int) -> List[Application]:
        """
        Generate Applications (12-15) with business/individual types, status distribution.
        
        Args:
            count: Number of applications to generate
            
        Returns:
            List of Application objects
        """
        self._update_status("applications", status="running", started_at=datetime.utcnow(), total=count, current=0)
        
        # Get demo applicants
        applicants = self.db.query(User).filter(User.role == UserRole.APPLICANT.value).all()
        if not applicants:
            raise ValueError("No applicant users found. Please seed demo users first.")
        
        applications = []
        status_distribution = {
            ApplicationStatus.DRAFT.value: 0.20,
            ApplicationStatus.SUBMITTED.value: 0.30,
            ApplicationStatus.UNDER_REVIEW.value: 0.30,
            ApplicationStatus.APPROVED.value: 0.15,
            ApplicationStatus.REJECTED.value: 0.05
        }
        
        for i in range(count):
            try:
                # Select application type (80% business, 20% individual)
                app_type = ApplicationType.BUSINESS.value if random.random() < 0.80 else ApplicationType.INDIVIDUAL.value
                
                # Select status based on distribution
                status = random.choices(
                    list(status_distribution.keys()),
                    weights=list(status_distribution.values())
                )[0]
                
                # Select applicant
                applicant = random.choice(applicants)
                
                # Generate application data
                loan_amount = random.randint(1000000, 50000000)
                years_in_business = random.randint(2, 50) if app_type == ApplicationType.BUSINESS.value else random.randint(1, 30)
                annual_revenue = loan_amount * random.uniform(2, 10)
                credit_score = random.randint(650, 850)
                
                application_data = {
                    "loan_amount": loan_amount,
                    "purpose": random.choice(["Working capital", "Expansion", "Refinancing", "Equipment purchase", "Inventory"]),
                    "industry": random.choice(["Technology", "Manufacturing", "Energy", "Healthcare", "Agriculture"]),
                    "years_in_business": years_in_business,
                    "annual_revenue": annual_revenue,
                    "credit_score": credit_score
                }
                
                business_data = None
                if app_type == ApplicationType.BUSINESS.value:
                    business_data = {
                        "company_name": f"Demo Company {i + 1}",
                        "tax_id": f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
                        "legal_structure": random.choice(["Corporation", "LLC", "Partnership"]),
                        "number_of_employees": random.randint(10, 5000),
                        "business_address": f"{random.randint(1, 9999)} Business St, City, ST {random.randint(10000, 99999)}"
                    }
                
                # Generate timestamps
                base_date = datetime.utcnow() - timedelta(days=random.randint(30, 180))
                submitted_at = base_date if status != ApplicationStatus.DRAFT.value else None
                reviewed_at = None
                approved_at = None
                rejected_at = None
                
                if status in [ApplicationStatus.UNDER_REVIEW.value, ApplicationStatus.APPROVED.value, ApplicationStatus.REJECTED.value]:
                    reviewed_at = submitted_at + timedelta(days=random.randint(1, 7)) if submitted_at else None
                
                if status == ApplicationStatus.APPROVED.value:
                    approved_at = reviewed_at + timedelta(days=random.randint(1, 14)) if reviewed_at else None
                
                if status == ApplicationStatus.REJECTED.value:
                    rejected_at = reviewed_at + timedelta(days=random.randint(1, 3)) if reviewed_at else None
                
                # Create application
                application = Application(
                    application_type=app_type,
                    status=status,
                    user_id=applicant.id,
                    submitted_at=submitted_at,
                    reviewed_at=reviewed_at,
                    approved_at=approved_at,
                    rejected_at=rejected_at,
                    application_data=application_data,
                    business_data=business_data
                )
                
                self.db.add(application)
                applications.append(application)
                self._update_status("applications", current=i + 1, progress=(i + 1) / count)
                
            except Exception as e:
                error_msg = f"Failed to generate application {i + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("applications", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("applications", status="completed", completed_at=datetime.utcnow())
        
        return applications
    
    def _create_deals_from_applications(self, applications: List[Application]) -> List[Deal]:
        """
        Create Deals from Applications with deal_id format, status mapping, deal_data JSONB.
        
        Args:
            applications: List of Application objects
            
        Returns:
            List of Deal objects
        """
        self._update_status("deals_creation", status="running", started_at=datetime.utcnow(), total=len(applications), current=0)
        
        deals = []
        now = datetime.utcnow()
        deal_id_prefix = f"DEAL-{now.year}-{now.month:02d}-"
        
        # Find the highest existing deal counter for this month to avoid conflicts
        existing_deals = self.db.query(Deal).filter(
            Deal.deal_id.like(f"{deal_id_prefix}%")
        ).all()
        
        max_counter = 0
        if existing_deals:
            for deal in existing_deals:
                try:
                    # Extract counter from deal_id (e.g., "DEAL-2026-01-001" -> 1)
                    counter_str = deal.deal_id.split("-")[-1]
                    counter = int(counter_str)
                    max_counter = max(max_counter, counter)
                except (ValueError, IndexError):
                    continue
        
        deal_counter = max_counter + 1
        
        for application in applications:
            try:
                # Only create deals for submitted+ applications
                if application.status == ApplicationStatus.DRAFT.value:
                    continue
                
                # Generate deal_id
                deal_id = f"{deal_id_prefix}{deal_counter:03d}"
                
                # Check if deal_id already exists, delete it and related data if it does
                existing_deal = self.db.query(Deal).filter(Deal.deal_id == deal_id).first()
                if existing_deal:
                    logger.info(f"Deleting existing demo deal {deal_id} and related data to overwrite with new data")
                    # Delete related data
                    self.db.query(Document).filter(Document.deal_id == existing_deal.id).delete()
                    self.db.query(DealNote).filter(DealNote.deal_id == existing_deal.id).delete()
                    # Delete workflows via documents (cascade should handle this, but be explicit)
                    doc_ids = [d.id for d in self.db.query(Document).filter(Document.deal_id == existing_deal.id).all()]
                    if doc_ids:
                        self.db.query(Workflow).filter(Workflow.document_id.in_(doc_ids)).delete()
                    # Delete the deal
                    self.db.delete(existing_deal)
                    self.db.flush()  # Flush to ensure deletion before creating new deal
                
                deal_counter += 1
                
                # Map application status to deal status
                status_mapping = {
                    ApplicationStatus.SUBMITTED.value: DealStatus.SUBMITTED.value,
                    ApplicationStatus.UNDER_REVIEW.value: DealStatus.UNDER_REVIEW.value,
                    ApplicationStatus.APPROVED.value: DealStatus.APPROVED.value,
                    ApplicationStatus.REJECTED.value: DealStatus.REJECTED.value
                }
                deal_status = status_mapping.get(application.status, DealStatus.SUBMITTED.value)
                
                # Add some active/closed deals (10% each)
                if random.random() < 0.10 and deal_status == DealStatus.APPROVED.value:
                    deal_status = DealStatus.ACTIVE.value
                elif random.random() < 0.10 and deal_status == DealStatus.ACTIVE.value:
                    deal_status = DealStatus.CLOSED.value
                
                # Get deal data from application
                loan_amount = application.application_data.get("loan_amount", 1000000) if application.application_data else 1000000
                interest_rate = random.uniform(3.5, 8.5)
                term_years = random.randint(1, 10)
                sustainability_linked = random.random() < 0.30  # 30% sustainability-linked
                
                deal_data = {
                    "loan_amount": loan_amount,
                    "interest_rate": interest_rate,
                    "term_years": term_years,
                    "collateral_type": random.choice(["Real Estate", "Equipment", "Inventory", "Accounts Receivable"]),
                    "sustainability_linked": sustainability_linked
                }
                
                if sustainability_linked:
                    deal_data["esg_targets"] = {
                        "ndvi_threshold": random.uniform(0.70, 0.85),
                        "verification_frequency": "Quarterly"
                    }
                
                # Create folder path
                folder_path = f"storage/deals/demo/{deal_id}/"
                
                # Create deal with is_demo flag
                deal = Deal(
                    deal_id=deal_id,
                    applicant_id=application.user_id,
                    application_id=application.id,
                    status=deal_status,
                    deal_type=DealType.LOAN_APPLICATION.value,
                    is_demo=True,  # Mark as demo deal
                    deal_data=deal_data,
                    folder_path=folder_path,
                    created_at=application.submitted_at or application.created_at,
                    updated_at=application.approved_at or application.reviewed_at or application.submitted_at or application.created_at
                )
                
                self.db.add(deal)
                deals.append(deal)
                
                self._update_status("deals_creation", current=len(deals), progress=len(deals) / len(applications))
                
            except Exception as e:
                error_msg = f"Failed to create deal from application {application.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("deals_creation", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("deals_creation", status="completed", completed_at=datetime.utcnow())
        
        return deals
    
    def _generate_deal_documents(self, deals: List[Deal]) -> List[Document]:
        """
        Generate deal documents (18-36) with title, borrower_name, borrower_lei, etc.
        
        Args:
            deals: List of Deal objects
            
        Returns:
            List of Document objects
        """
        self._update_status("documents", status="running", started_at=datetime.utcnow(), total=len(deals) * 2, current=0)
        
        documents = []
        # Get demo users for document uploaders
        uploaders = self.db.query(User).filter(
            User.role.in_([UserRole.BANKER.value, UserRole.LAW_OFFICER.value, UserRole.ACCOUNTANT.value])
        ).all()
        
        if not uploaders:
            uploaders = self.db.query(User).limit(3).all()
        
        for deal in deals:
            try:
                # Check if documents already exist for this deal, skip if they do
                existing_docs = self.db.query(Document).filter(Document.deal_id == deal.id).all()
                if existing_docs:
                    logger.debug(f"Documents already exist for deal {deal.deal_id}, skipping document generation")
                    documents.extend(existing_docs)
                    continue
                
                # Generate 1-3 documents per deal
                doc_count = random.randint(1, 3)
                
                for doc_idx in range(doc_count):
                    # Generate CDM for this document
                    cdm = self._generate_cdm_for_deal(
                        deal_type=deal.deal_type,
                        seed=deal.id + doc_idx
                    )
                    
                    # Extract borrower info from CDM
                    borrower = next((p for p in cdm.parties if p.role == "Borrower"), None) if cdm.parties else None
                    borrower_name = borrower.name if borrower else f"Borrower {deal.deal_id}"
                    borrower_lei = borrower.lei if borrower else None
                    
                    # Calculate total commitment
                    total_commitment = Decimal(0)
                    currency = "USD"
                    if cdm.facilities:
                        for facility in cdm.facilities:
                            if facility.commitment_amount:
                                total_commitment += facility.commitment_amount.amount
                                currency = facility.commitment_amount.currency.value if hasattr(facility.commitment_amount.currency, 'value') else str(facility.commitment_amount.currency)
                    
                    # Document title
                    doc_titles = [
                        f"Credit Agreement - {borrower_name}",
                        f"Term Sheet - {deal.deal_id}",
                        f"Supporting Documents - {deal.deal_id}"
                    ]
                    title = doc_titles[doc_idx] if doc_idx < len(doc_titles) else f"Document {doc_idx + 1} - {deal.deal_id}"
                    
                    # ESG metadata
                    esg_metadata = None
                    sustainability_linked = deal.deal_data.get("sustainability_linked", False) if deal.deal_data else False
                    if sustainability_linked:
                        esg_metadata = {
                            "esg_score": random.uniform(0.65, 0.95),
                            "kpi_targets": ["NDVI > 0.75", "Carbon reduction 20%"],
                            "verification_frequency": random.choice(["Quarterly", "Annual"])
                        }
                    
                    # Create document
                    # Note: is_demo is tracked via deal.deal_data["is_demo"], not a separate field
                    document = Document(
                        title=title,
                        borrower_name=borrower_name,
                        borrower_lei=borrower_lei,
                        governing_law=cdm.governing_law or "NY",
                        total_commitment=total_commitment,
                        currency=currency,
                        agreement_date=cdm.agreement_date,
                        sustainability_linked=sustainability_linked,
                        esg_metadata=esg_metadata,
                        uploaded_by=random.choice(uploaders).id if uploaders else None,
                        deal_id=deal.id,
                        created_at=deal.created_at + timedelta(days=random.randint(0, 2))
                    )
                    
                    self.db.add(document)
                    documents.append(document)
                    self._update_status("documents", current=len(documents), progress=len(documents) / (len(deals) * 2))
                    
            except Exception as e:
                error_msg = f"Failed to generate document for deal {deal.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("documents", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("documents", status="completed", completed_at=datetime.utcnow())
        
        return documents
    
    def _create_document_versions(self, documents: List[Document]) -> List[DocumentVersion]:
        """
        Create DocumentVersions (24-48) with version_number, extracted_text, extracted_data (CDM JSON).
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of DocumentVersion objects
        """
        self._update_status("document_versions", status="running", started_at=datetime.utcnow(), total=len(documents) * 1.5, current=0)
        
        document_versions = []
        
        for document in documents:
            try:
                # Check if versions already exist for this document, skip if they do
                existing_versions = self.db.query(DocumentVersion).filter(
                    DocumentVersion.document_id == document.id
                ).all()
                if existing_versions:
                    logger.debug(f"Document versions already exist for document {document.id}, skipping version generation")
                    document_versions.extend(existing_versions)
                    # Ensure current_version_id is set
                    if not document.current_version_id and existing_versions:
                        document.current_version_id = existing_versions[0].id
                    continue
                
                # Generate 1-2 versions per document
                version_count = random.randint(1, 2)
                
                for version_num in range(1, version_count + 1):
                    # Generate CDM data for this document
                    cdm = self._generate_cdm_for_deal(
                        deal_type="loan_application",
                        seed=document.id + version_num
                    )
                    
                    # Generate extracted text (first 5000 chars of simulated document)
                    extracted_text = f"""CREDIT AGREEMENT

This Credit Agreement (the "Agreement") is entered into on {cdm.agreement_date or '2024-01-15'} 
between the parties listed herein.

BORROWER: {document.borrower_name or 'Borrower'}
LEI: {document.borrower_lei or 'N/A'}

FACILITY DETAILS:
"""
                    if cdm.facilities:
                        for facility in cdm.facilities:
                            extracted_text += f"""
Facility Name: {facility.facility_name}
Commitment Amount: {facility.commitment_amount.amount} {facility.commitment_amount.currency}
Maturity Date: {facility.maturity_date}
Interest Rate: {facility.interest_terms.rate_option.benchmark} + {facility.interest_terms.rate_option.spread_bps} bps
"""
                    
                    extracted_text = extracted_text[:5000]  # Limit to 5000 chars
                    
                    # Check if this version already exists, skip if it does
                    existing_version = self.db.query(DocumentVersion).filter(
                        DocumentVersion.document_id == document.id,
                        DocumentVersion.version_number == version_num
                    ).first()
                    if existing_version:
                        logger.debug(f"Document version {version_num} already exists for document {document.id}, skipping")
                        document_versions.append(existing_version)
                        continue
                    
                    # Create document version
                    # Use model_dump_json() and parse to ensure dates are serialized as strings for JSONB storage
                    import json
                    cdm_json = cdm.model_dump_json()
                    cdm_dict = json.loads(cdm_json)
                    doc_version = DocumentVersion(
                        document_id=document.id,
                        version_number=version_num,
                        original_text=extracted_text,  # Use original_text, not extracted_text
                        extracted_data=cdm_dict,
                        created_at=document.created_at + timedelta(days=random.randint(0, 2))
                    )
                    
                    self.db.add(doc_version)
                    # Flush to get the ID before updating document's current_version_id
                    self.db.flush()
                    document_versions.append(doc_version)
                    
                    # Update document's current_version_id if this is version 1
                    if version_num == 1:
                        document.current_version_id = doc_version.id
                        # Also set source_cdm_data for easier access
                        document.source_cdm_data = cdm_dict
                    
                    self._update_status("document_versions", current=len(document_versions), progress=len(document_versions) / (len(documents) * 1.5))
                
            except Exception as e:
                error_msg = f"Failed to create document version for document {document.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("document_versions", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("document_versions", status="completed", completed_at=datetime.utcnow())
        
        return document_versions
    
    def create_document_revision_history(self, document_ids: List[int]) -> List[DocumentVersion]:
        """
        Generate document revision history (30% of documents get version 2, 3) with modified CDM data.
        
        Args:
            document_ids: List of document IDs to create revision history for
            
        Returns:
            List of additional DocumentVersion objects (versions 2, 3)
        """
        self._update_status("document_revisions", status="running", started_at=datetime.utcnow(), total=len(document_ids), current=0)
        
        additional_versions = []
        
        # Handle empty document list
        if not document_ids:
            self._update_status("document_revisions", status="skipped", completed_at=datetime.utcnow())
            return additional_versions
        
        # Select 30% of documents for revision history
        sample_size = max(1, int(len(document_ids) * 0.30))
        # Ensure sample size doesn't exceed population
        sample_size = min(sample_size, len(document_ids))
        documents_to_revise = random.sample(document_ids, sample_size)
        
        for document_id in documents_to_revise:
            try:
                document = self.db.query(Document).filter(Document.id == document_id).first()
                if not document:
                    continue
                
                # Get existing versions to find max version number
                existing_versions = self.db.query(DocumentVersion).filter(
                    DocumentVersion.document_id == document_id
                ).order_by(DocumentVersion.version_number.desc()).all()
                
                max_version = max([v.version_number for v in existing_versions]) if existing_versions else 1
                
                # Create 1-2 additional versions (version 2, 3)
                num_additional = random.randint(1, 2)
                
                for i in range(num_additional):
                    version_num = max_version + i + 1
                    
                    # Get base CDM from previous version
                    base_version = existing_versions[0] if existing_versions else None
                    base_cdm = None
                    
                    if base_version and base_version.extracted_data:
                        try:
                            from app.models.cdm import CreditAgreement
                            base_cdm = CreditAgreement(**base_version.extracted_data)
                        except Exception:
                            pass
                    
                    if not base_cdm:
                        # Generate new CDM
                        base_cdm = self._generate_cdm_for_deal(deal_type="loan_application", seed=document_id + version_num)
                    else:
                        # Modify CDM slightly (simulate edits)
                        # Change amounts, dates, or other fields
                        if base_cdm.facilities and len(base_cdm.facilities) > 0:
                            # Modify commitment amount slightly
                            original_amount = base_cdm.facilities[0].commitment_amount.amount
                            modification_factor = random.uniform(0.95, 1.05)  # ±5% change
                            new_amount = Decimal(str(float(original_amount) * modification_factor))
                            base_cdm.facilities[0].commitment_amount.amount = new_amount
                        
                        # Update agreement date
                        if base_cdm.agreement_date:
                            base_cdm.agreement_date = base_cdm.agreement_date + timedelta(days=random.randint(-5, 5))
                    
                    # Generate modified extracted text
                    extracted_text = f"""CREDIT AGREEMENT (REVISED VERSION {version_num})

This Credit Agreement (the "Agreement") is entered into on {base_cdm.agreement_date or '2024-01-15'} 
between the parties listed herein.

BORROWER: {document.borrower_name or 'Borrower'}
LEI: {document.borrower_lei or 'N/A'}

FACILITY DETAILS (REVISED):
"""
                    if base_cdm.facilities:
                        for facility in base_cdm.facilities:
                            extracted_text += f"""
Facility Name: {facility.facility_name}
Commitment Amount: {facility.commitment_amount.amount} {facility.commitment_amount.currency}
Maturity Date: {facility.maturity_date}
Interest Rate: {facility.interest_terms.rate_option.benchmark} + {facility.interest_terms.rate_option.spread_bps} bps
"""
                    
                    extracted_text = extracted_text[:5000]
                    
                    # Check if this version already exists, skip if it does
                    existing_version = self.db.query(DocumentVersion).filter(
                        DocumentVersion.document_id == document_id,
                        DocumentVersion.version_number == version_num
                    ).first()
                    if existing_version:
                        logger.debug(f"Document version {version_num} already exists for document {document_id}, skipping")
                        additional_versions.append(existing_version)
                        continue
                    
                    # Create document version
                    # Use model_dump_json() and parse to ensure dates are serialized as strings for JSONB storage
                    import json
                    cdm_json = base_cdm.model_dump_json()
                    cdm_dict = json.loads(cdm_json)
                    doc_version = DocumentVersion(
                        document_id=document_id,
                        version_number=version_num,
                        original_text=extracted_text,  # Use original_text, not extracted_text
                        extracted_data=cdm_dict,
                        created_at=document.created_at + timedelta(days=random.randint(1, 5))
                    )
                    
                    self.db.add(doc_version)
                    additional_versions.append(doc_version)
                    
                    # Link to workflow state transitions
                    # Version 2 → under_review state (if exists)
                    # Version 3 → approved state (if exists)
                    workflow = self.db.query(Workflow).filter(Workflow.document_id == document_id).first()
                    if workflow:
                        if version_num == 2 and workflow.state == WorkflowState.UNDER_REVIEW.value:
                            workflow.submitted_at = doc_version.created_at
                        elif version_num == 3 and workflow.state == WorkflowState.APPROVED.value:
                            workflow.approved_at = doc_version.created_at
                    
                    self._update_status("document_revisions", current=len(additional_versions), progress=len(additional_versions) / len(documents_to_revise))
                
            except Exception as e:
                error_msg = f"Failed to create revision history for document {document_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("document_revisions", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("document_revisions", status="completed", completed_at=datetime.utcnow())
        
        return additional_versions
    
    def _create_workflows_for_documents(self, documents: List[Document]) -> List[Workflow]:
        """
        Create Workflows (18-36) with state distribution, assigned_to, approved_by, timestamps.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of Workflow objects
        """
        self._update_status("workflows", status="running", started_at=datetime.utcnow(), total=len(documents), current=0)
        
        workflows = []
        # Get reviewers and approvers
        reviewers = self.db.query(User).filter(
            User.role.in_([UserRole.LAW_OFFICER.value, UserRole.REVIEWER.value, UserRole.ADMIN.value])
        ).all()
        creators = self.db.query(User).filter(
            User.role.in_([UserRole.BANKER.value, UserRole.ANALYST.value])
        ).all()
        
        if not reviewers:
            reviewers = self.db.query(User).limit(3).all()
        if not creators:
            creators = self.db.query(User).limit(2).all()
        
        state_distribution = {
            WorkflowState.DRAFT.value: 0.30,
            WorkflowState.UNDER_REVIEW.value: 0.40,
            WorkflowState.APPROVED.value: 0.20,
            WorkflowState.PUBLISHED.value: 0.10
        }
        
        for document in documents:
            try:
                # Check if workflow already exists for this document, skip if it does
                existing_workflow = self.db.query(Workflow).filter(Workflow.document_id == document.id).first()
                if existing_workflow:
                    logger.debug(f"Workflow already exists for document {document.id}, skipping workflow creation")
                    workflows.append(existing_workflow)
                    continue
                
                # Select state based on distribution
                state = random.choices(
                    list(state_distribution.keys()),
                    weights=list(state_distribution.values())
                )[0]
                
                # Assign based on state
                assigned_to = None
                if state == WorkflowState.UNDER_REVIEW.value:
                    assigned_to = random.choice(reviewers).id if reviewers else None
                elif state == WorkflowState.DRAFT.value:
                    assigned_to = random.choice(creators).id if creators else None
                elif state in [WorkflowState.APPROVED.value, WorkflowState.PUBLISHED.value]:
                    assigned_to = random.choice(reviewers).id if reviewers else None
                
                # Generate timestamps
                submitted_at = None
                approved_at = None
                published_at = None
                
                if state in [WorkflowState.UNDER_REVIEW.value, WorkflowState.APPROVED.value, WorkflowState.PUBLISHED.value]:
                    submitted_at = document.created_at + timedelta(days=random.randint(1, 3))
                
                if state in [WorkflowState.APPROVED.value, WorkflowState.PUBLISHED.value]:
                    approved_at = submitted_at + timedelta(days=random.randint(1, 7)) if submitted_at else None
                
                if state == WorkflowState.PUBLISHED.value:
                    published_at = approved_at + timedelta(days=random.randint(1, 3)) if approved_at else None
                
                # Select approver
                approved_by = random.choice(reviewers).id if reviewers and state in [WorkflowState.APPROVED.value, WorkflowState.PUBLISHED.value] else None
                
                # Priority
                priority = random.choices(
                    ["normal", "high", "urgent"],
                    weights=[0.70, 0.25, 0.05]
                )[0]
                
                # Due date
                due_date = None
                if state == WorkflowState.UNDER_REVIEW.value and submitted_at:
                    due_date = submitted_at + timedelta(days=random.randint(7, 14))
                
                # Create workflow
                workflow = Workflow(
                    document_id=document.id,
                    state=state,
                    assigned_to=assigned_to,
                    submitted_at=submitted_at,
                    approved_at=approved_at,
                    approved_by=approved_by,
                    published_at=published_at,
                    priority=priority,
                    due_date=due_date
                )
                
                self.db.add(workflow)
                workflows.append(workflow)
                self._update_status("workflows", current=len(workflows), progress=len(workflows) / len(documents))
                
            except Exception as e:
                error_msg = f"Failed to create workflow for document {document.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("workflows", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("workflows", status="completed", completed_at=datetime.utcnow())
        
        return workflows
    
    def _generate_loan_assets_for_deals(self, deals: List[Deal]) -> List[LoanAsset]:
        """
        Generate LoanAssets (4-6) for sustainability-linked deals.
        
        Args:
            deals: List of Deal objects
            
        Returns:
            List of LoanAsset objects
        """
        # Filter sustainability-linked deals
        sustainability_deals = [
            deal for deal in deals
            if deal.deal_data and deal.deal_data.get("sustainability_linked", False)
        ]
        
        if not sustainability_deals:
            return []
        
        self._update_status("loan_assets", status="running", started_at=datetime.utcnow(), total=len(sustainability_deals), current=0)
        
        loan_assets = []
        
        for deal in sustainability_deals:
            try:
                # Get ESG targets from deal
                esg_targets = deal.deal_data.get("esg_targets", {}) if deal.deal_data else {}
                ndvi_threshold = esg_targets.get("ndvi_threshold", 0.75)
                
                # Generate realistic address
                addresses = [
                    "123 Industrial Way, Detroit, MI 48201",
                    "456 Farm Road, Napa, CA 94558",
                    "789 Agricultural Blvd, Fresno, CA 93721",
                    "321 Green Valley Lane, Austin, TX 78701"
                ]
                collateral_address = random.choice(addresses)
                
                # Generate coordinates (rough geocoding)
                geo_coords = {
                    "123 Industrial Way, Detroit, MI 48201": (42.3314, -83.0458),
                    "456 Farm Road, Napa, CA 94558": (38.2975, -122.2869),
                    "789 Agricultural Blvd, Fresno, CA 93721": (36.7378, -119.7871),
                    "321 Green Valley Lane, Austin, TX 78701": (30.2672, -97.7431)
                }
                geo_lat, geo_lon = geo_coords.get(collateral_address, (40.7128, -74.0060))
                
                # Generate NDVI score
                last_verified_score = random.uniform(0.50, 0.95)
                
                # Calculate risk status
                if last_verified_score >= ndvi_threshold:
                    risk_status = "COMPLIANT"
                elif last_verified_score >= ndvi_threshold * 0.9:
                    risk_status = "WARNING"
                else:
                    risk_status = "BREACH"
                
                # Get interest rate
                base_interest_rate = deal.deal_data.get("interest_rate", 5.25) if deal.deal_data else 5.25
                penalty_bps = esg_targets.get("penalty_bps", 25) if isinstance(esg_targets, dict) else 25
                current_interest_rate = base_interest_rate + (penalty_bps / 10000 if risk_status == "BREACH" else 0)
                
                # SPT data
                spt_data = {
                    "target_type": "NDVI",
                    "threshold": ndvi_threshold,
                    "measurement_frequency": "Quarterly",
                    "penalty_bps": penalty_bps
                }
                
                # Asset metadata
                asset_metadata = {
                    "verification_method": "Sentinel-2B",
                    "cloud_cover": random.uniform(0.01, 0.10),
                    "classification": random.choice(["AnnualCrop", "Forest", "PermanentCrop"]),
                    "confidence": random.uniform(0.85, 0.98)
                }
                
                # Generate green finance metrics (synthetic for demo)
                # Location classification based on address pattern
                location_type_map = {
                    "123 Industrial Way, Detroit, MI 48201": "urban",
                    "456 Farm Road, Napa, CA 94558": "rural",
                    "789 Agricultural Blvd, Fresno, CA 93721": "suburban",
                    "321 Green Valley Lane, Austin, TX 78701": "suburban"
                }
                location_type = location_type_map.get(collateral_address, random.choice(["urban", "suburban", "rural"]))
                location_confidence = random.uniform(0.75, 0.95)
                
                # Generate air quality data (synthetic)
                # Urban areas typically have higher AQI, rural lower
                if location_type == "urban":
                    aqi = random.uniform(80, 150)  # Moderate to Unhealthy for Sensitive Groups
                    pm25 = random.uniform(25, 55)
                    pm10 = random.uniform(50, 100)
                    no2 = random.uniform(30, 80)
                elif location_type == "suburban":
                    aqi = random.uniform(50, 100)  # Good to Moderate
                    pm25 = random.uniform(12, 35)
                    pm10 = random.uniform(30, 70)
                    no2 = random.uniform(15, 50)
                else:  # rural
                    aqi = random.uniform(20, 60)  # Good
                    pm25 = random.uniform(5, 20)
                    pm10 = random.uniform(10, 40)
                    no2 = random.uniform(5, 25)
                
                # Generate OSM metrics (synthetic)
                if location_type == "urban":
                    building_count = random.randint(500, 2000)
                    building_density = random.uniform(50, 150)  # buildings/km²
                    road_density = random.uniform(8, 15)  # km/km²
                    green_infrastructure_coverage = random.uniform(0.10, 0.25)  # 10-25%
                elif location_type == "suburban":
                    building_count = random.randint(100, 500)
                    building_density = random.uniform(20, 50)  # buildings/km²
                    road_density = random.uniform(5, 10)  # km/km²
                    green_infrastructure_coverage = random.uniform(0.25, 0.40)  # 25-40%
                else:  # rural
                    building_count = random.randint(10, 100)
                    building_density = random.uniform(2, 20)  # buildings/km²
                    road_density = random.uniform(2, 6)  # km/km²
                    green_infrastructure_coverage = random.uniform(0.40, 0.70)  # 40-70%
                
                # Calculate sustainability components
                # Normalize NDVI to 0-1 (already is)
                vegetation_health = last_verified_score
                
                # Normalize AQI to 0-1 (inverse: lower AQI = better = higher score)
                # AQI 0-50 = 1.0, 51-100 = 0.8, 101-150 = 0.6, 151-200 = 0.4, 201+ = 0.2
                if aqi <= 50:
                    air_quality_score = 1.0
                elif aqi <= 100:
                    air_quality_score = 0.8
                elif aqi <= 150:
                    air_quality_score = 0.6
                elif aqi <= 200:
                    air_quality_score = 0.4
                else:
                    air_quality_score = 0.2
                
                # Urban activity (inverse: less activity = better for sustainability)
                # Based on building/road density
                activity_score = max(0.0, 1.0 - (building_density / 200.0) - (road_density / 20.0))
                
                # Green infrastructure (direct: more green = better)
                green_infra_score = green_infrastructure_coverage
                
                # Pollution levels (inverse: less pollution = better)
                pollution_score = max(0.0, 1.0 - (aqi / 300.0))
                
                # Calculate composite sustainability score (weighted average)
                # Using default weights from config
                sustainability_components = {
                    "vegetation_health": vegetation_health,
                    "air_quality": air_quality_score,
                    "urban_activity": activity_score,
                    "green_infrastructure": green_infra_score,
                    "pollution_levels": pollution_score
                }
                
                # Default weights (matching config defaults)
                weights = {
                    "vegetation_health": 0.30,
                    "air_quality": 0.25,
                    "urban_activity": 0.15,
                    "green_infrastructure": 0.20,
                    "pollution_levels": 0.10
                }
                
                composite_sustainability_score = (
                    sustainability_components["vegetation_health"] * weights["vegetation_health"] +
                    sustainability_components["air_quality"] * weights["air_quality"] +
                    sustainability_components["urban_activity"] * weights["urban_activity"] +
                    sustainability_components["green_infrastructure"] * weights["green_infrastructure"] +
                    sustainability_components["pollution_levels"] * weights["pollution_levels"]
                )
                
                # Build green finance metrics dict
                green_finance_metrics = {
                    "location_type": location_type,
                    "location_confidence": location_confidence,
                    "osm_metrics": {
                        "building_count": building_count,
                        "building_density": building_density,
                        "road_density": road_density,
                        "green_infrastructure_coverage": green_infrastructure_coverage
                    },
                    "air_quality": {
                        "pm25": pm25,
                        "pm10": pm10,
                        "no2": no2,
                        "data_source": "synthetic_demo"
                    },
                    "sustainability_components": sustainability_components
                }
                
                # Create loan asset with green finance metrics
                loan_asset = LoanAsset(
                    loan_id=deal.deal_id,
                    original_text=f"Credit agreement for {deal.deal_id} with sustainability-linked provisions.",
                    collateral_address=collateral_address,
                    geo_lat=geo_lat,
                    geo_lon=geo_lon,
                    spt_data=spt_data,
                    spt_threshold=ndvi_threshold,
                    last_verified_score=last_verified_score,
                    risk_status=risk_status,
                    base_interest_rate=float(base_interest_rate),
                    current_interest_rate=float(current_interest_rate),
                    penalty_bps=penalty_bps if risk_status == "BREACH" else 0,
                    last_verified_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                    asset_metadata=asset_metadata,
                    # Green Finance Metrics
                    location_type=location_type,
                    air_quality_index=aqi,
                    composite_sustainability_score=composite_sustainability_score,
                    green_finance_metrics=green_finance_metrics
                )
                
                # Add to session - SQLModel works with SQLAlchemy sessions
                try:
                    self.db.add(loan_asset)
                    self.db.flush()  # Flush to get ID and validate
                    loan_assets.append(loan_asset)
                    self._update_status("loan_assets", current=len(loan_assets), progress=len(loan_assets) / len(sustainability_deals))
                except Exception as db_error:
                    # Rollback the failed add
                    self.db.rollback()
                    error_msg = f"Failed to add loan asset to database for deal {deal.id}: {str(db_error)}"
                    logger.error(error_msg, exc_info=True)
                    logger.error(f"LoanAsset data: loan_id={deal.deal_id}, risk_status={risk_status}, base_rate={base_interest_rate}, current_rate={current_interest_rate}")
                    self._update_status("loan_assets", errors=[error_msg])
                    continue
                
            except Exception as e:
                error_msg = f"Failed to generate loan asset for deal {deal.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                logger.error(f"Exception type: {type(e).__name__}, args: {e.args}")
                self._update_status("loan_assets", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("loan_assets", status="completed", completed_at=datetime.utcnow())
        
        return loan_assets
    
    def generate_documents_from_templates(self, deal_id: int) -> List[GeneratedDocument]:
        """
        Generate documents from templates for approved deals (12-24 GeneratedDocuments).
        
        Args:
            deal_id: Deal ID to generate documents for
            
        Returns:
            List of GeneratedDocument objects
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Only generate for approved deals
        if deal.status not in [DealStatus.APPROVED.value, DealStatus.ACTIVE.value]:
            logger.info(f"Skipping template generation for deal {deal_id} (status: {deal.status})")
            return []
        
        self._update_status("generated_documents", status="running", started_at=datetime.utcnow(), total=2, current=0)
        
        # Get available templates
        from app.db.models import LMATemplate
        templates = self.db.query(LMATemplate).filter(LMATemplate.is_active == True).all()
        
        if not templates:
            logger.warning("No active templates found for document generation")
            return []
        
        # Select 1-2 templates per deal
        selected_templates = random.sample(templates, min(random.randint(1, 2), len(templates)))
        
        # Get primary document for CDM data
        primary_doc = self.db.query(Document).filter(
            Document.deal_id == deal_id
        ).order_by(Document.created_at.asc()).first()
        
        if not primary_doc:
            logger.warning(f"No primary document found for deal {deal_id}")
            return []
        
        # Get CDM data from primary document's version
        cdm_data = None
        if primary_doc.current_version_id:
            doc_version = self.db.query(DocumentVersion).filter(
                DocumentVersion.id == primary_doc.current_version_id
            ).first()
            if doc_version and doc_version.extracted_data:
                try:
                    from app.models.cdm import CreditAgreement
                    cdm_data = CreditAgreement(**doc_version.extracted_data)
                except Exception as e:
                    logger.warning(f"Failed to parse CDM data from document version: {e}")
        
        if not cdm_data:
            # Generate CDM if not available
            cdm_data = self._generate_cdm_for_deal(deal_type=deal.deal_type, seed=deal.id)
        
        # Get demo users for document creators
        creators = self.db.query(User).filter(
            User.role.in_([UserRole.BANKER.value, UserRole.LAW_OFFICER.value])
        ).all()
        if not creators:
            creators = self.db.query(User).limit(2).all()
        
        generated_docs = []
        
        try:
            from app.generation.service import DocumentGenerationService
            gen_service = DocumentGenerationService()
            
            for template in selected_templates:
                try:
                    # Generate document
                    generated_doc = gen_service.generate_document(
                        db=self.db,
                        template_id=template.id,
                        cdm_data=cdm_data,
                        user_id=random.choice(creators).id if creators else None,
                        source_document_id=primary_doc.id,
                        deal_id=deal.id
                    )
                    
                    # Update status distribution
                    status_dist = random.choices(
                        [GeneratedDocumentStatus.DRAFT.value, GeneratedDocumentStatus.REVIEW.value, 
                         GeneratedDocumentStatus.APPROVED.value, GeneratedDocumentStatus.EXECUTED.value],
                        weights=[0.40, 0.40, 0.15, 0.05]
                    )[0]
                    generated_doc.status = status_dist
                    
                    # Update file path to demo folder
                    if generated_doc.file_path:
                        # Ensure it's in the demo deal folder
                        if "storage/deals/demo" not in generated_doc.file_path:
                            generated_doc.file_path = f"storage/deals/demo/{deal.deal_id}/generated/{template.template_code}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.docx"
                    
                    # Update generation summary
                    if generated_doc.generation_summary:
                        generated_doc.generation_summary["cache_hits"] = random.randint(0, 3)
                        generated_doc.generation_summary["generation_time_seconds"] = random.uniform(2.5, 8.0)
                    
                    generated_docs.append(generated_doc)
                    self._update_status("generated_documents", current=len(generated_docs), progress=len(generated_docs) / len(selected_templates))
                    
                except Exception as e:
                    error_msg = f"Failed to generate document from template {template.id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self._update_status("generated_documents", errors=[error_msg])
                    continue
            
            self.db.commit()
            self._update_status("generated_documents", status="completed", completed_at=datetime.utcnow())
            
        except Exception as e:
            error_msg = f"Failed to initialize DocumentGenerationService: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._update_status("generated_documents", status="failed", completed_at=datetime.utcnow(), errors=[error_msg])
        
        return generated_docs
    
    def create_deal_notes(self, deal_ids: List[int]) -> List[DealNote]:
        """
        Create DealNotes (24-60) from different users with note_type distribution.
        
        Args:
            deal_ids: List of deal IDs to create notes for
            
        Returns:
            List of DealNote objects
        """
        self._update_status("deal_notes", status="running", started_at=datetime.utcnow(), total=len(deal_ids) * 3, current=0)
        
        deal_notes = []
        
        # Get users for note creation
        all_users = self.db.query(User).all()
        user_roles = {
            UserRole.BANKER.value: [u for u in all_users if u.role == UserRole.BANKER.value],
            UserRole.LAW_OFFICER.value: [u for u in all_users if u.role == UserRole.LAW_OFFICER.value],
            UserRole.ACCOUNTANT.value: [u for u in all_users if u.role == UserRole.ACCOUNTANT.value],
            UserRole.REVIEWER.value: [u for u in all_users if u.role == UserRole.REVIEWER.value],
            UserRole.APPLICANT.value: [u for u in all_users if u.role == UserRole.APPLICANT.value]
        }
        
        note_templates = {
            "general": [
                "Reviewed credit agreement. Borrower credit score is strong.",
                "Deal progressing well. All documentation in order.",
                "Following up on outstanding items.",
                "Deal status update: All parties aligned."
            ],
            "verification": [
                "Legal review complete. All clauses comply with regulations.",
                "Compliance check passed. No issues identified.",
                "Verification completed successfully.",
                "All required documentation verified."
            ],
            "status_change": [
                "Approved for proceeding to next stage.",
                "Status updated to approved.",
                "Deal moved to active status.",
                "Workflow transition completed."
            ],
            "financial": [
                "Financial analysis shows positive cash flow projections.",
                "Credit analysis complete. Borrower meets all criteria.",
                "Financial review indicates strong credit profile.",
                "Cash flow analysis supports loan approval."
            ]
        }
        
        for deal_id in deal_ids:
            try:
                deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
                if not deal:
                    continue
                
                # Create 2-5 notes per deal
                note_count = random.randint(2, 5)
                
                for i in range(note_count):
                    # Select user role based on distribution
                    role_weights = {
                        UserRole.BANKER.value: 0.30,
                        UserRole.LAW_OFFICER.value: 0.25,
                        UserRole.ACCOUNTANT.value: 0.20,
                        UserRole.REVIEWER.value: 0.15,
                        UserRole.APPLICANT.value: 0.10
                    }
                    
                    selected_role = random.choices(
                        list(role_weights.keys()),
                        weights=list(role_weights.values())
                    )[0]
                    
                    users_for_role = user_roles.get(selected_role, [])
                    if not users_for_role:
                        users_for_role = all_users
                    
                    user = random.choice(users_for_role)
                    
                    # Select note type
                    note_type = random.choices(
                        ["general", "verification", "status_change", "financial"],
                        weights=[0.50, 0.20, 0.20, 0.10]
                    )[0]
                    
                    # Generate note content
                    content = random.choice(note_templates.get(note_type, note_templates["general"]))
                    
                    # Get related document if available
                    related_doc = self.db.query(Document).filter(
                        Document.deal_id == deal_id
                    ).first()
                    
                    note_metadata = {
                        "related_document_id": related_doc.id if related_doc else None,
                        "priority": random.choice(["normal", "high"]),
                        "tags": [note_type, selected_role]
                    }
                    
                    # Generate timestamps across deal lifecycle
                    base_date = deal.created_at
                    note_date = base_date + timedelta(days=random.randint(0, (datetime.utcnow() - base_date).days))
                    
                    # Create note
                    note = DealNote(
                        deal_id=deal_id,
                        user_id=user.id,
                        content=content,
                        note_type=note_type,
                        note_metadata=note_metadata,
                        created_at=note_date,
                        updated_at=note_date + timedelta(days=random.randint(0, 2)) if random.random() < 0.20 else None
                    )
                    
                    self.db.add(note)
                    deal_notes.append(note)
                    self._update_status("deal_notes", current=len(deal_notes), progress=len(deal_notes) / (len(deal_ids) * 3))
                
            except Exception as e:
                error_msg = f"Failed to create notes for deal {deal_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("deal_notes", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("deal_notes", status="completed", completed_at=datetime.utcnow())
        
        return deal_notes
    
    def create_policy_decisions_for_documents(self, document_ids: List[int]) -> List[PolicyDecision]:
        """
        Create PolicyDecisions (18-36) for documents with decision distribution.
        
        Args:
            document_ids: List of document IDs to create policy decisions for
            
        Returns:
            List of PolicyDecision objects
        """
        self._update_status("policy_decisions", status="running", started_at=datetime.utcnow(), total=len(document_ids), current=0)
        
        policy_decisions = []
        
        # Policy rules
        policy_rules = [
            "block_sanctioned_parties",
            "flag_high_risk_jurisdiction",
            "check_collateral_requirements",
            "verify_esg_compliance",
            "check_credit_limits",
            "verify_kyc_compliance"
        ]
        
        for document_id in document_ids:
            try:
                document = self.db.query(Document).filter(Document.id == document_id).first()
                if not document:
                    continue
                
                # Only create for documents in workflow (submitted+)
                workflow = self.db.query(Workflow).filter(Workflow.document_id == document_id).first()
                if not workflow or workflow.state == WorkflowState.DRAFT.value:
                    continue
                
                # Select decision based on distribution
                decision = random.choices(
                    ["ALLOW", "FLAG", "BLOCK"],
                    weights=[0.70, 0.20, 0.10]
                )[0]
                
                # Select rule
                rule_applied = random.choice(policy_rules)
                
                # Generate CDM event
                import uuid
                from app.models.cdm_events import generate_cdm_policy_evaluation
                
                transaction_id = document.deal.deal_id if document.deal else f"DOC-{document_id}"
                
                policy_event = generate_cdm_policy_evaluation(
                    transaction_id=transaction_id,
                    transaction_type="facility_creation",
                    decision=decision,
                    rule_applied=rule_applied,
                    related_event_identifiers=[],
                    evaluation_trace=[{
                        "rule": rule_applied,
                        "decision": decision,
                        "document_id": document_id
                    }],
                    matched_rules=[rule_applied]
                )
                
                # Create policy decision
                policy_decision = PolicyDecision(
                    transaction_id=transaction_id,
                    transaction_type="facility_creation",
                    decision=decision,
                    rule_applied=rule_applied,
                    trace_id=str(uuid.uuid4()),
                    document_id=document_id,
                    trace=[{
                        "rule": rule_applied,
                        "decision": decision,
                        "document_id": document_id
                    }],
                    matched_rules=[rule_applied],
                    cdm_events=policy_event,
                    created_at=workflow.submitted_at or document.created_at
                )
                
                self.db.add(policy_decision)
                policy_decisions.append(policy_decision)
                self._update_status("policy_decisions", current=len(policy_decisions), progress=len(policy_decisions) / len(document_ids))
                
            except Exception as e:
                error_msg = f"Failed to create policy decision for document {document_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("policy_decisions", errors=[error_msg])
                continue
        
        self.db.commit()
        
        self._update_status("policy_decisions", status="completed", completed_at=datetime.utcnow())
        
        return policy_decisions
    
    def _create_green_finance_policy_decisions(
        self,
        loan_assets: List[LoanAsset],
        deals: List[Deal]
    ) -> List[PolicyDecision]:
        """
        Create green finance policy decisions for demo loan assets.
        
        Args:
            loan_assets: List of LoanAsset objects
            deals: List of Deal objects (for deal_id mapping)
            
        Returns:
            List of PolicyDecision objects
        """
        if not loan_assets:
            return []
        
        policy_decisions = []
        deal_id_map = {deal.deal_id: deal.id for deal in deals}
        
        try:
            from app.services.policy_service import PolicyService
            from app.services.policy_engine_factory import get_policy_engine
            from app.models.cdm import CreditAgreement
            
            policy_service = PolicyService(get_policy_engine())
            
            for loan_asset in loan_assets:
                try:
                    if not loan_asset.geo_lat or not loan_asset.geo_lon:
                        continue
                    
                    deal_id = deal_id_map.get(loan_asset.loan_id)
                    
                    # Get deal for credit agreement context
                    deal = next((d for d in deals if d.deal_id == loan_asset.loan_id), None)
                    
                    # Create basic CreditAgreement for evaluation
                    credit_agreement = None
                    if deal:
                        credit_agreement = CreditAgreement(
                            deal_id=deal.deal_id,
                            loan_identification_number=deal.deal_id,
                            sustainability_linked=deal.deal_data.get("sustainability_linked", False) if deal.deal_data else False
                        )
                    
                    # Evaluate green finance compliance
                    green_finance_result = policy_service.evaluate_green_finance_compliance(
                        credit_agreement=credit_agreement,
                        loan_asset=loan_asset,
                        document_id=None
                    )
                    
                    # Create PolicyDecision
                    policy_decision = PolicyDecision(
                        transaction_id=loan_asset.loan_id,
                        deal_id=deal_id,
                        loan_asset_id=loan_asset.id,
                        decision=green_finance_result.decision,
                        rule_applied=green_finance_result.rule_applied,
                        trace_id=green_finance_result.trace_id,
                        policy_evaluation_trace=green_finance_result.trace,
                        matched_rules=green_finance_result.matched_rules,
                        created_at=datetime.utcnow()
                    )
                    
                    self.db.add(policy_decision)
                    policy_decisions.append(policy_decision)
                    
                except Exception as e:
                    logger.warning(f"Failed to create green finance policy decision for loan asset {loan_asset.id}: {e}")
                    continue
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create green finance policy decisions: {e}", exc_info=True)
            self.db.rollback()
        
        return policy_decisions
    
    def _create_green_finance_assessments(
        self,
        loan_assets: List[LoanAsset],
        deals: List[Deal]
    ) -> List[GreenFinanceAssessment]:
        """
        Create green finance assessments for demo loan assets.
        
        Args:
            loan_assets: List of LoanAsset objects
            deals: List of Deal objects (for deal_id mapping)
            
        Returns:
            List of GreenFinanceAssessment objects
        """
        if not loan_assets:
            return []
        
        self._update_status("green_finance_assessments", status="running", 
                          started_at=datetime.utcnow(), total=len(loan_assets), current=0)
        
        assessments = []
        deal_id_map = {deal.deal_id: deal.id for deal in deals}
        
        for loan_asset in loan_assets:
            try:
                if not loan_asset.geo_lat or not loan_asset.geo_lon:
                    continue
                
                # Get deal_id from loan_id
                deal_id = deal_id_map.get(loan_asset.loan_id)
                
                # Extract green finance metrics
                green_metrics = loan_asset.green_finance_metrics or {}
                osm_metrics = green_metrics.get("osm_metrics", {})
                air_quality = green_metrics.get("air_quality", {})
                sustainability_components = green_metrics.get("sustainability_components", {})
                
                # Build environmental metrics
                environmental_metrics = {
                    "air_quality_index": loan_asset.air_quality_index,
                    "pm25": air_quality.get("pm25"),
                    "pm10": air_quality.get("pm10"),
                    "no2": air_quality.get("no2")
                }
                
                # Build urban activity metrics
                urban_activity_metrics = {
                    "building_count": osm_metrics.get("building_count"),
                    "building_density": osm_metrics.get("building_density"),
                    "road_density": osm_metrics.get("road_density"),
                    "green_infrastructure_coverage": osm_metrics.get("green_infrastructure_coverage")
                }
                
                # Calculate SDG alignment (simplified for demo)
                sdg_alignment = {
                    "sdg_11": min(1.0, (loan_asset.composite_sustainability_score or 0.5) * 1.1),  # Sustainable Cities
                    "sdg_13": min(1.0, (1.0 - (loan_asset.air_quality_index or 100) / 300.0)),  # Climate Action
                    "sdg_15": loan_asset.last_verified_score or 0.5,  # Life on Land (NDVI)
                    "overall_alignment": loan_asset.composite_sustainability_score or 0.5,
                    "aligned_goals": [],
                    "needs_improvement": []
                }
                
                # Determine aligned goals (>=70%) and needs improvement (<50%)
                for goal, score in [("SDG 11", sdg_alignment["sdg_11"]), 
                                   ("SDG 13", sdg_alignment["sdg_13"]), 
                                   ("SDG 15", sdg_alignment["sdg_15"])]:
                    if score >= 0.7:
                        sdg_alignment["aligned_goals"].append(goal)
                    elif score < 0.5:
                        sdg_alignment["needs_improvement"].append(goal)
                
                # Create assessment
                assessment = GreenFinanceAssessment(
                    transaction_id=loan_asset.loan_id,
                    deal_id=deal_id,
                    loan_asset_id=loan_asset.id,
                    location_lat=loan_asset.geo_lat,
                    location_lon=loan_asset.geo_lon,
                    location_type=loan_asset.location_type,
                    location_confidence=green_metrics.get("location_confidence"),
                    environmental_metrics=environmental_metrics,
                    urban_activity_metrics=urban_activity_metrics,
                    sustainability_score=loan_asset.composite_sustainability_score,
                    sustainability_components=sustainability_components,
                    sdg_alignment=sdg_alignment,
                    assessed_at=loan_asset.last_verified_at or datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.db.add(assessment)
                assessments.append(assessment)
                self._update_status("green_finance_assessments", 
                                  current=len(assessments), 
                                  progress=len(assessments) / len(loan_assets))
                
            except Exception as e:
                error_msg = f"Failed to create green finance assessment for loan asset {loan_asset.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("green_finance_assessments", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("green_finance_assessments", status="completed", 
                          completed_at=datetime.utcnow())
        
        return assessments
    
    def _create_deal_storage(self, deal_id: str) -> Path:
        """
        Create storage structure for a deal.
        
        Args:
            deal_id: Deal ID
            
        Returns:
            Path to deal storage directory
        """
        from app.services.file_storage_service import FileStorageService
        
        file_storage = FileStorageService()
        
        # Create deal folder structure
        # Note: FileStorageService.create_deal_folder expects user_id, but for demo we'll use a default
        # We'll create the demo-specific structure manually
        base_path = Path("storage/deals/demo") / deal_id
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (base_path / "documents").mkdir(exist_ok=True)
        (base_path / "extractions").mkdir(exist_ok=True)
        (base_path / "generated").mkdir(exist_ok=True)
        (base_path / "notes").mkdir(exist_ok=True)
        
        logger.debug(f"Created storage structure for deal {deal_id} at {base_path}")
        return base_path
    
    def _store_generated_documents(self, deals: List[Deal], documents: List[Document], document_versions: List[DocumentVersion], generated_docs: List[GeneratedDocument]) -> None:
        """
        Store generated documents as files (TXT, DOCX, JSON) using FileStorageService.
        
        Args:
            deals: List of Deal objects
            documents: List of Document objects
            document_versions: List of DocumentVersion objects
            generated_docs: List of GeneratedDocument objects
        """
        self._update_status("file_storage", status="running", started_at=datetime.utcnow(), total=len(document_versions) + len(generated_docs), current=0)
        
        from app.services.file_storage_service import FileStorageService
        import json
        
        file_storage = FileStorageService()
        
        # Store document versions as TXT and JSON
        for doc_version in document_versions:
            try:
                document = next((d for d in documents if d.id == doc_version.document_id), None)
                if not document or not document.deal:
                    continue
                
                deal_id = document.deal.deal_id
                storage_path = self._create_deal_storage(deal_id)
                
                # Store extracted text as TXT
                txt_file = storage_path / "documents" / f"document_{document.id}_v{doc_version.version_number}.txt"
                with open(txt_file, "w", encoding="utf-8") as f:
                    f.write(doc_version.original_text or "")  # Use original_text, not extracted_text
                
                # Store CDM JSON in extractions folder
                if doc_version.extracted_data:
                    json_file = storage_path / "extractions" / f"document_{document.id}_v{doc_version.version_number}_cdm.json"
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(doc_version.extracted_data, f, indent=2, default=str)
                
                self._update_status("file_storage", current=self._status.get("file_storage", SeedingStatus("file_storage")).current + 1)
                
            except Exception as e:
                error_msg = f"Failed to store document version {doc_version.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("file_storage", errors=[error_msg])
                continue
        
        # Store generated documents (already have file_path set by DocumentGenerationService)
        # Just ensure they're in the right location
        for gen_doc in generated_docs:
            try:
                if gen_doc.source_document:
                    deal = gen_doc.source_document.deal
                    if deal:
                        deal_id = deal.deal_id
                        storage_path = self._create_deal_storage(deal_id)
                        
                        # Update file path if needed
                        if gen_doc.file_path and "storage/deals/demo" not in gen_doc.file_path:
                            # Move to generated folder
                            filename = Path(gen_doc.file_path).name
                            new_path = storage_path / "generated" / filename
                            gen_doc.file_path = str(new_path)
                            
                            # If file exists at old path, move it
                            old_path = Path(gen_doc.file_path)
                            if old_path.exists():
                                new_path.parent.mkdir(parents=True, exist_ok=True)
                                import shutil
                                shutil.move(str(old_path), str(new_path))
                
                self._update_status("file_storage", current=self._status.get("file_storage", SeedingStatus("file_storage")).current + 1)
                
            except Exception as e:
                error_msg = f"Failed to store generated document {gen_doc.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self._update_status("file_storage", errors=[error_msg])
                continue
        
        self.db.commit()
        self._update_status("file_storage", status="completed", completed_at=datetime.utcnow())
    
    def index_demo_documents(self, document_ids: List[int]) -> int:
        """
        Load documents into ChromaDB using DocumentRetrievalService with embeddings and metadata.
        
        Args:
            document_ids: List of document IDs to index
            
        Returns:
            Number of documents indexed
        """
        self._update_status("chromadb_indexing", status="running", started_at=datetime.utcnow(), total=len(document_ids), current=0)
        
        indexed_count = 0
        
        try:
            from app.chains.document_retrieval_chain import DocumentRetrievalService
            from app.core.llm_client import get_embeddings_model
            
            doc_retrieval = DocumentRetrievalService(collection_name="creditnexus_documents")
            embeddings_model = get_embeddings_model()
            
            for document_id in document_ids:
                try:
                    document = self.db.query(Document).filter(Document.id == document_id).first()
                    if not document:
                        continue
                    
                    # Get document version with extracted text
                    doc_version = None
                    if document.current_version_id:
                        doc_version = self.db.query(DocumentVersion).filter(
                            DocumentVersion.id == document.current_version_id
                        ).first()
                    
                    if not doc_version or not doc_version.original_text:
                        logger.warning(f"Document {document_id} has no original text, skipping ChromaDB indexing")
                        continue
                    
                    # Generate embedding
                    text = doc_version.original_text[:10000]  # Limit text length - use original_text, not extracted_text
                    embedding = embeddings_model.embed_query(text)
                    
                    # Prepare metadata
                    metadata = {
                        "document_id": str(document.id),
                        "deal_id": str(document.deal_id) if document.deal_id else None,
                        "borrower_name": document.borrower_name or "",
                        "is_demo": "true",
                        "created_at": document.created_at.isoformat() if document.created_at else None,
                        "title": document.title or ""
                    }
                    
                    # Add to ChromaDB
                    doc_retrieval.collection.add(
                        ids=[f"demo_doc_{document_id}"],
                        embeddings=[embedding],
                        documents=[text],
                        metadatas=[{k: str(v) if v is not None else "" for k, v in metadata.items()}]
                    )
                    
                    indexed_count += 1
                    self._update_status("chromadb_indexing", current=indexed_count, progress=indexed_count / len(document_ids))
                    
                except Exception as e:
                    error_msg = f"Failed to index document {document_id} in ChromaDB: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self._update_status("chromadb_indexing", errors=[error_msg])
                    continue
            
            self._update_status("chromadb_indexing", status="completed", completed_at=datetime.utcnow())
            
        except ImportError:
            logger.warning("ChromaDB not available, skipping document indexing")
            self._update_status("chromadb_indexing", status="skipped", completed_at=datetime.utcnow())
        except Exception as e:
            error_msg = f"Failed to initialize ChromaDB indexing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._update_status("chromadb_indexing", status="failed", completed_at=datetime.utcnow(), errors=[error_msg])
        
        # Create index.json in ChromaDB seed folder
        try:
            chroma_seed_path = Path("chroma_db/seeds/demo")
            chroma_seed_path.mkdir(parents=True, exist_ok=True)
            
            index_data = {
                "collection": "creditnexus_documents",
                "demo_documents": indexed_count,
                "indexed_at": datetime.utcnow().isoformat(),
                "metadata_tags": {
                    "is_demo": "true",
                    "source": "demo_data_service",
                    "document_count": indexed_count
                },
                "document_ids": [str(doc_id) for doc_id in document_ids[:indexed_count]]
            }
            
            index_file = chroma_seed_path / "index.json"
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2, default=str)
            
            logger.info(f"Created ChromaDB seed index at {index_file}")
            
        except Exception as e:
            logger.warning(f"Failed to create ChromaDB seed index: {e}")
        
        return indexed_count
