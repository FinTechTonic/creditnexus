# Summary of New Changes

This document summarizes the new changes pulled from the `main` branch.

## Commit Range

- **Start:** `fe8a54f`
- **End:** `7e572a6`

## Overview of Changes

- **197 files changed**
- **51565 insertions(+)**
- **2015 deletions(-)**

## Detailed Changes by File

| File | Changes |
|---|---|
| .cursor.tar | Bin 0 -> 83456 bytes |
| .env.example | 135 + |
| .github/workflows/deploy-project-site.yml | 62 + |
| .github/workflows/mintlify-deploy.yml | 26 + |
| .gitignore | 14 + |
| .python-version | 9 + |
| README.md | 137 +- |
| alembic/client/package-lock.json | 343 + |
| alembic/client/package.json | 7 + |
| alembic/versions/4b5c6d7e8f9a_add_policy_decisions_table.py | 79 + |
| alembic/versions/5887d0638b42_merge_migration_heads.py | 28 + |
| alembic/versions/5c6d7e8f9a0b_add_payment_events_table.py | 97 + |
| alembic/versions/5d8daddcc33f_add_clause_cache_table.py | 85 + |
| alembic/versions/6d7e8f9a0b1c_add_lma_templates_tables.py | 111 + |
| alembic/versions/781c3c4131c9_add_password_hash_column_to_users_table.py | 31 +- |
| alembic/versions/7f8a9b0c1d2e_add_applications_inquiries_meetings_wallet.py | 122 + |
| alembic/versions/9e814a37d6dc_add_lma_generation_fields_to_documents.py | 54 + |
| alembic/versions/dcf895ebe666_merge_clause_cache_with_existing_heads.py | 28 + |
| alembic/versions/e6043869162a_add_metadata_column_to_loan_assets.py | 29 + |
| alembic/versions/e650a2d25272_create_base_tables_documents_workflows_.py | 188 + |
| app/agents/analyzer.py | 224 +- |
| app/agents/audit_workflow.py | 240 +- |
| app/api/routes.py | 7941 ++++++++++++++++---- |
| app/chains/audio_transcription_chain.py | 304 + |
| app/chains/decision_support_chain.py | 588 ++ |
| app/chains/document_retrieval_chain.py | 358 + |
| app/chains/extraction_chain.py | 191 +- |
| app/chains/image_extraction_chain.py | 408 + |
| app/chains/map_reduce_chain.py | 30 +- |
| app/chains/multimodal_fusion_chain.py | 709 ++ |
| app/chains/template_aware_extraction.py | 349 + |
| app/core/config.py | 166 +- |
| app/core/llm_client.py | 505 ++ |
| app/core/policy_config.py | 261 + |
| app/db/__init__.py | 53 +- |
| app/db/models.py | 611 +- |
| app/generation/__init__.py | 21 + |
| app/generation/analyzer.py | 407 + |
| app/generation/field_parser.py | 366 + |
| app/generation/mapper.py | 413 + |
| app/generation/populator.py | 396 + |
| app/generation/renderer.py | 794 ++ |
| app/generation/service.py | 308 + |
| app/models/cdm.py | 341 + |
| app/models/cdm_events.py | 139 +- |
| app/models/cdm_payment.py | 309 + |
| app/models/cdm_state_machine.py | 128 + |
| app/models/loan_asset.py | 17 + |
| app/policies/__init__.py | 18 + |
| app/policies/syndicated_loan_rules.yaml | 223 + |
| app/prompts/templates/__init__.py | 21 + |
| app/prompts/templates/confidentiality.py | 97 + |
| app/prompts/templates/facility_agreement.py | 1771 +++++ |
| app/prompts/templates/loader.py | 332 + |
| app/prompts/templates/origination.py | 103 + |
| app/prompts/templates/regional.py | 73 + |
| app/prompts/templates/regulatory.py | 357 + |
| app/prompts/templates/restructuring.py | 133 + |
| app/prompts/templates/secondary_trading.py | 231 + |
| app/prompts/templates/security_intercreditor.py | 228 + |
| app/prompts/templates/supporting.py | 103 + |
| app/prompts/templates/sustainable_finance.py | 234 + |
| app/prompts/templates/term_sheet.py | 162 + |
| app/services/__init__.py | 18 + |
| app/services/clause_cache_service.py | 289 + |
| app/services/ics_generator.py | 112 + |
| app/services/payment_processor.py | 276 + |
| app/services/payment_scheduler.py | 214 + |
| app/services/policy_audit.py | 293 + |
| app/services/policy_engine_factory.py | 107 + |
| app/services/policy_engine_interface.py | 239 + |
| app/services/policy_service.py | 574 ++ |
| app/services/x402_payment_service.py | 256 + |
| app/templates/__init__.py | 21 + |
| app/templates/registry.py | 227 + |
| app/templates/storage.py | 230 + |
| app/utils/json_serializer.py | 71 + |
| app/utils/load_chroma_seeds.py | 178 + |
| chroma_db/chroma.sqlite3 | Bin 0 -> 167936 bytes |
| client/package-lock.json | 492 +- |
| client/package.json | 10 +- |
| client/src/App.tsx | 89 +- |
| client/src/apps/application/BusinessApplicationForm.tsx | 933 +++ |
| client/src/apps/application/IndividualApplicationForm.tsx | 713 ++ |
| client/src/apps/docu-digitizer/DocumentParser.tsx | 402 +- |
| client/src/apps/docu-digitizer/MultimodalInputTabs.tsx | 265 + |
| client/src/apps/document-generator/AudioRecorder.tsx | 396 + |
| client/src/apps/document-generator/CdmDataPreview.tsx | 311 + |
| client/src/apps/document-generator/CdmPreviewCard.tsx | 185 + |
| client/src/apps/document-generator/ChatbotPanel.tsx | 516 ++ |
| client/src/apps/document-generator/DataInputForm.tsx | 462 ++ |
| client/src/apps/document-generator/DocumentCdmSelector.tsx | 352 + |
| client/src/apps/document-generator/DocumentGenerator.tsx | 777 ++ |
| client/src/apps/document-generator/DocumentPreview.tsx | 261 + |
| client/src/apps/document-generator/DocumentSearch.tsx | 392 + |
| client/src/apps/document-generator/ExportDialog.tsx | 220 + |
| client/src/apps/document-generator/FieldEditorModal.tsx | 438 ++ |
| client/src/apps/document-generator/FieldFillingPanel.tsx | 472 ++ |
| client/src/apps/document-generator/FloatingChatbotButton.tsx | 69 + |
| client/src/apps/document-generator/ImageUploader.tsx | 496 ++ |
| client/src/apps/document-generator/InputTabs.tsx | 165 + |
| client/src/apps/document-generator/MultimodalInputPanel.tsx | 650 ++ |
| client/src/apps/document-generator/PreGenerationStats.tsx | 401 + |
| client/src/apps/document-generator/ProcessingStatus.tsx | 425 ++ |
| client/src/apps/document-generator/TemplateGrid.tsx | 213 + |
| client/src/apps/document-generator/TemplateSelector.tsx | 174 + |
| client/src/apps/document-generator/UnifiedSelectionGrid.tsx | 201 + |
| client/src/apps/document-generator/__init__.ts | 17 + |
| client/src/apps/trade-blotter/TradeBlotter.tsx | 452 +- |
| client/src/components/ApplicationDashboard.tsx | 393 + |
| client/src/components/ApplicationStatusTracker.tsx | 311 + |
| client/src/components/CalendarView.tsx | 285 + |
| client/src/components/CdmFieldEditor.tsx | 345 + |
| client/src/components/ClauseEditor.tsx | 393 + |
| client/src/components/Dashboard.tsx | 167 +- |
| client/src/components/DesktopAppLayout.tsx | 569 ++ |
| client/src/components/DocumentHistory.tsx | 330 +- |
| client/src/components/ErrorBoundary.tsx | 134 + |
| client/src/components/Footer.tsx | 159 + |
| client/src/components/Inbox.tsx | 362 + |
| client/src/components/InquiryDetail.tsx | 417 + |
| client/src/components/InquiryForm.tsx | 264 + |
| client/src/components/LoginForm.tsx | 15 +- |
| client/src/components/MainNavigation.tsx | 300 + |
| client/src/components/MeetingModal.tsx | 500 ++ |
| client/src/components/MetaMaskConnect.tsx | 170 + |
| client/src/components/TemplateLibrary.tsx | 326 + |
| client/src/components/WorkflowActions.tsx | 48 +- |
| client/src/components/ui/badge.tsx | 36 + |
| client/src/components/ui/dialog.tsx | 185 + |
| client/src/components/ui/label.tsx | 24 + |
| client/src/components/ui/loading-states.tsx | 166 + |
| client/src/components/ui/progress.tsx | 26 + |
| client/src/components/ui/textarea.tsx | 19 + |
| client/src/context/AuthContext.tsx | 20 +- |
| client/src/context/FDC3Context.tsx | 22 +- |
| client/src/context/WalletContext.tsx | 218 + |
| client/src/main.tsx | 27 +- |
| client/src/pages/LoginPage.tsx | 30 + |
| client/src/router/Routes.tsx | 237 + |
| client/src/sites/businesses/BusinessApplicationFlow.tsx | 188 + |
| client/src/sites/businesses/BusinessLanding.tsx | 298 + |
| client/src/sites/individuals/IndividualApplicationFlow.tsx | 142 + |
| client/src/sites/individuals/IndividualLanding.tsx | 221 + |
| client/src/sites/metamask/MetaMaskLogin.tsx | 232 + |
| client/src/sites/payments/DisbursementPage.tsx | 341 + |
| client/src/sites/payments/ReceiptPage.tsx | 315 + |
| client/src/utils/icsDownload.ts | 43 + |
| client/vite.config.ts | 5 + |
| data/templates_metadata.json | 801 ++ |
| docs/api-reference/authentication.mdx | 60 + |
| docs/api-reference/documents.mdx | 67 + |
| docs/architecture/cdm-compliance.mdx | 47 + |
| docs/architecture/overview.mdx | 44 + |
| docs/docs.json | 77 + |
| docs/field_coverage_analysis.md | 142 + |
| docs/getting-started/how-to-use.mdx | 167 + |
| docs/getting-started/installation.mdx | 128 + |
| docs/getting-started/introduction.mdx | 51 + |
| docs/getting-started/quickstart.mdx | 79 + |
| docs/guides/document-extraction.mdx | 94 + |
| docs/guides/document-generation.mdx | 104 + |
| docs/guides/trade-execution.mdx | 118 + |
| docs/guides/verification.mdx | 109 + |
| package-lock.json | 477 ++ |
| package.json | 6 + |
| project-site/README.md | 18 + |
| project-site/index.html | 14 + |
| project-site/package-lock.json | 2742 +++++++ |
| project-site/package.json | 26 + |
| project-site/postcss.config.js | 6 + |
| project-site/src/App.tsx | 366 + |
| project-site/src/index.css | 24 + |
| project-site/src/main.tsx | 10 + |
| project-site/tailwind.config.js | 11 + |
| project-site/tsconfig.json | 21 + |
| project-site/tsconfig.node.json | 10 + |
| project-site/vite.config.ts | 23 + |
| pyproject.toml | 141 + |
| replit.md | 205 - |
| requirements.txt | 43 - |
| sample_credit_agreement.txt | 2 +- |
| sampleloanagreement.txt | 1 + |
| scripts/create_demo_user.py | 83 + |
| scripts/create_template_files.py | 491 ++ |
| scripts/generate_dummy_templates.py | 322 + |
| main.py => scripts/main.py | 0 |
| main_long_doc.py => scripts/main_long_doc.py | 0 |
| scripts/run_dev.py | 35 + |
| scripts/seed_field_mappings.py | 156 + |
| scripts/seed_templates.py | 452 ++ |
| scripts/setup_chatbot_kb.py | 529 ++ |
| scripts/update_demo_user_email.py | 53 + |
| scripts/validate_templates.py | 326 + |
| verify_env.py => scripts/verify_env.py | 0 |
| scripts/verify_mappings.py | 20 + |
| server.py | 294 +- |
