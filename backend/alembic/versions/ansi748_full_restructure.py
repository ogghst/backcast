"""ANSI-748 full restructure of project domain tables.

Revision ID: ansi748_full_restructure
Revises: d20fe84ef4df
Create Date: 2026-05-26

Replaces the existing project domain schema with ANSI-748 compliant
structure:
- departments -> organizational_units (hierarchical OBS, branchable)
- wbes -> wbs_elements (branchable)
- package_types -> cost_event_types
- work_packages (old QualityEvent) -> cost_events (versionable)
- NEW: control_accounts (branchable, links WBS + OBS)
- NEW: work_packages (PMI WorkPackage, under control_account, branchable)
- cost_elements: now EOC under WorkPackage (versionable only)
- progress_entries: FK to work_package_id instead of cost_element_id
- cost_registrations: cost_event_id instead of work_package_id

All project-related tables are dropped and recreated. Non-project tables
(users, AI, documents, RBAC, etc.) are preserved with their current schema.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ansi748_full_restructure"
down_revision = "d20fe84ef4df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # PHASE 1: DROP ALL PROJECT-RELATED TABLES (dependency order)
    # ========================================================================
    op.execute("DROP TABLE IF EXISTS progress_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_registration_attachments CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_registrations CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_elements CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_element_types CASCADE")
    op.execute("DROP TABLE IF EXISTS schedule_baselines CASCADE")
    op.execute("DROP TABLE IF EXISTS forecasts CASCADE")
    op.execute("DROP TABLE IF EXISTS work_packages CASCADE")
    op.execute("DROP TABLE IF EXISTS package_types CASCADE")
    op.execute("DROP TABLE IF EXISTS wbes CASCADE")
    op.execute("DROP TABLE IF EXISTS departments CASCADE")
    op.execute("DROP TABLE IF EXISTS change_orders CASCADE")
    op.execute("DROP TABLE IF EXISTS project_budget_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS change_order_audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS co_approval_rule_config CASCADE")
    op.execute("DROP TABLE IF EXISTS co_impact_level_config CASCADE")
    op.execute("DROP TABLE IF EXISTS co_sla_rule_config CASCADE")
    op.execute("DROP TABLE IF EXISTS co_config_audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS co_workflow_config CASCADE")
    op.execute("DROP TABLE IF EXISTS branches CASCADE")
    # Drop and recreate projects last among domain tables
    op.execute("DROP TABLE IF EXISTS projects CASCADE")

    # ========================================================================
    # PHASE 2: CREATE TABLES IN DEPENDENCY ORDER (ANSI-748 schema)
    # ========================================================================

    # --- 1. organizational_units (was departments, now hierarchical OBS) ---
    op.execute("""
        CREATE TABLE organizational_units (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organizational_unit_id UUID NOT NULL,
            parent_unit_id UUID,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            manager_id UUID,
            is_active BOOLEAN NOT NULL DEFAULT true,
            description TEXT,

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_org_units_organizational_unit_id "
        "ON organizational_units (organizational_unit_id)"
    )
    op.execute(
        "CREATE INDEX ix_org_units_parent_unit_id "
        "ON organizational_units (parent_unit_id)"
    )
    op.execute(
        "CREATE INDEX ix_org_units_code ON organizational_units (code)"
    )
    op.execute(
        "CREATE INDEX ix_org_units_valid_time "
        "ON organizational_units USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_org_units_transaction_time "
        "ON organizational_units USING gist (transaction_time)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_org_units_ou_id_branch_current "
        "ON organizational_units (organizational_unit_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- 2. cost_element_types (reference data, versionable only) ---
    op.execute("""
        CREATE TABLE cost_element_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_element_type_id UUID NOT NULL,
            organizational_unit_id UUID NOT NULL,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,

            -- EVCS versionable fields (NOT branchable)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cet_cost_element_type_id "
        "ON cost_element_types (cost_element_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_cet_organizational_unit_id "
        "ON cost_element_types (organizational_unit_id)"
    )
    op.execute(
        "CREATE INDEX ix_cet_code ON cost_element_types (code)"
    )
    op.execute(
        "CREATE INDEX ix_cet_valid_time "
        "ON cost_element_types USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_cet_transaction_time "
        "ON cost_element_types USING gist (transaction_time)"
    )

    # --- 3. cost_event_types (was package_types, versionable only) ---
    op.execute("""
        CREATE TABLE cost_event_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_event_type_id UUID NOT NULL,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            color VARCHAR(30) NOT NULL DEFAULT 'blue',
            is_quality BOOLEAN NOT NULL DEFAULT false,
            description TEXT,

            -- EVCS versionable fields (NOT branchable)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cetyp_cost_event_type_id "
        "ON cost_event_types (cost_event_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_cetyp_code ON cost_event_types (code)"
    )
    op.execute(
        "CREATE INDEX ix_cetyp_valid_time "
        "ON cost_event_types USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_cetyp_transaction_time "
        "ON cost_event_types USING gist (transaction_time)"
    )

    # --- 4. projects (same structure, branchable + versionable) ---
    op.execute("""
        CREATE TABLE projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL,
            contract_value NUMERIC(15,2),
            currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
            status VARCHAR(20) NOT NULL,
            start_date TIMESTAMPTZ,
            end_date TIMESTAMPTZ,
            description TEXT,

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_projects_project_id ON projects (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_projects_code ON projects (code)"
    )
    op.execute(
        "CREATE INDEX ix_projects_name ON projects (name)"
    )
    op.execute(
        "CREATE INDEX ix_projects_status ON projects (status)"
    )
    op.execute(
        "CREATE INDEX ix_projects_created_by ON projects (created_by)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_projects_project_id_branch_current "
        "ON projects (project_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL "
        "AND NOT isempty(valid_time)"
    )

    # --- 5. wbs_elements (was wbes, branchable + versionable) ---
    op.execute("""
        CREATE TABLE wbs_elements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            wbs_element_id UUID NOT NULL,
            project_id UUID NOT NULL,
            parent_wbs_element_id UUID,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            revenue_allocation NUMERIC(15,2),
            level INTEGER NOT NULL DEFAULT 1,
            description TEXT,

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_wbs_elements_wbs_element_id "
        "ON wbs_elements (wbs_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_project_id "
        "ON wbs_elements (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_parent_wbs_element_id "
        "ON wbs_elements (parent_wbs_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_code ON wbs_elements (code)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_name ON wbs_elements (name)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_level ON wbs_elements (level)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_created_by "
        "ON wbs_elements (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_valid_time "
        "ON wbs_elements USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_wbs_elements_transaction_time "
        "ON wbs_elements USING gist (transaction_time)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_wbs_elements_wbs_element_id_branch_current "
        "ON wbs_elements (wbs_element_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- 6. control_accounts (NEW, branchable + versionable) ---
    op.execute("""
        CREATE TABLE control_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            control_account_id UUID NOT NULL,
            wbs_element_id UUID NOT NULL,
            organizational_unit_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50),
            description TEXT,

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_ca_control_account_id "
        "ON control_accounts (control_account_id)"
    )
    op.execute(
        "CREATE INDEX ix_ca_wbs_element_id "
        "ON control_accounts (wbs_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_ca_organizational_unit_id "
        "ON control_accounts (organizational_unit_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ca_ca_id_branch_current "
        "ON control_accounts (control_account_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ca_wbs_org_branch_current "
        "ON control_accounts (wbs_element_id, organizational_unit_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- 7. work_packages (NEW PMI WorkPackage, branchable + versionable) ---
    op.execute("""
        CREATE TABLE work_packages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            work_package_id UUID NOT NULL,
            control_account_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL,
            budget_amount NUMERIC(15,2) NOT NULL DEFAULT 0,
            schedule_baseline_id UUID,
            forecast_id UUID,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'open',

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_wp_work_package_id "
        "ON work_packages (work_package_id)"
    )
    op.execute(
        "CREATE INDEX ix_wp_control_account_id "
        "ON work_packages (control_account_id)"
    )
    op.execute(
        "CREATE INDEX ix_wp_code ON work_packages (code)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_wp_schedule_baseline_current "
        "ON work_packages (schedule_baseline_id) "
        "WHERE schedule_baseline_id IS NOT NULL "
        "AND upper(valid_time) IS NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_wp_forecast_current "
        "ON work_packages (forecast_id) "
        "WHERE forecast_id IS NOT NULL "
        "AND upper(valid_time) IS NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_wp_wp_id_branch_current "
        "ON work_packages (work_package_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- 8. cost_elements (EOC under WorkPackage, versionable only) ---
    op.execute("""
        CREATE TABLE cost_elements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_element_id UUID NOT NULL,
            work_package_id UUID NOT NULL,
            cost_element_type_id UUID NOT NULL,
            amount NUMERIC(15,2) NOT NULL DEFAULT 0,
            description TEXT,

            -- EVCS versionable fields (NOT branchable)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_ce_cost_element_id "
        "ON cost_elements (cost_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_ce_work_package_id "
        "ON cost_elements (work_package_id)"
    )
    op.execute(
        "CREATE INDEX ix_ce_cost_element_type_id "
        "ON cost_elements (cost_element_type_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ce_cost_element_id_current "
        "ON cost_elements (cost_element_id) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- 9. cost_events (was work_packages/QualityImpact, versionable only) ---
    op.execute("""
        CREATE TABLE cost_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_event_id UUID NOT NULL,
            project_id UUID NOT NULL,
            wbs_element_id UUID,
            name VARCHAR(255) NOT NULL,
            cost_event_type_id UUID NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            external_event_id VARCHAR(100),
            event_date TIMESTAMPTZ,
            coq_category VARCHAR(30),
            estimated_impact NUMERIC(15,2) NOT NULL DEFAULT 0,
            schedule_impact_days SMALLINT,

            -- EVCS versionable fields (NOT branchable)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cev_cost_event_id "
        "ON cost_events (cost_event_id)"
    )
    op.execute(
        "CREATE INDEX ix_cev_project_id ON cost_events (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_cev_wbs_element_id "
        "ON cost_events (wbs_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_cev_cost_event_type_id "
        "ON cost_events (cost_event_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_cev_external_event_id "
        "ON cost_events (external_event_id)"
    )
    op.execute(
        "CREATE INDEX ix_cev_created_by "
        "ON cost_events (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_cev_valid_time "
        "ON cost_events USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_cev_transaction_time "
        "ON cost_events USING gist (transaction_time)"
    )

    # --- 10. schedule_baselines (versionable + branchable) ---
    op.execute("""
        CREATE TABLE schedule_baselines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            schedule_baseline_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            start_date TIMESTAMPTZ NOT NULL,
            end_date TIMESTAMPTZ NOT NULL,
            progression_type VARCHAR(20) NOT NULL DEFAULT 'LINEAR',
            description TEXT,

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_sb_schedule_baseline_id "
        "ON schedule_baselines (schedule_baseline_id)"
    )
    op.execute(
        "CREATE INDEX ix_sb_name ON schedule_baselines (name)"
    )
    op.execute(
        "CREATE INDEX ix_sb_start_date ON schedule_baselines (start_date)"
    )
    op.execute(
        "CREATE INDEX ix_sb_end_date ON schedule_baselines (end_date)"
    )
    op.execute(
        "CREATE INDEX ix_sb_created_by ON schedule_baselines (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_sb_branch ON schedule_baselines (branch)"
    )
    op.execute(
        "CREATE INDEX ix_sb_valid_time "
        "ON schedule_baselines USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_sb_transaction_time "
        "ON schedule_baselines USING gist (transaction_time)"
    )

    # --- 11. forecasts (versionable + branchable) ---
    op.execute("""
        CREATE TABLE forecasts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            forecast_id UUID NOT NULL,
            eac_amount NUMERIC(15,2) NOT NULL,
            basis_of_estimate TEXT NOT NULL,
            approved_date TIMESTAMPTZ,
            approved_by UUID,

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR(80) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(80)
        )
    """)
    op.execute(
        "CREATE INDEX ix_f_forecast_id ON forecasts (forecast_id)"
    )
    op.execute(
        "CREATE INDEX ix_f_created_by ON forecasts (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_f_approved_by ON forecasts (approved_by) "
        "WHERE approved_by IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_f_branch ON forecasts (branch)"
    )
    op.execute(
        "CREATE INDEX ix_f_valid_time "
        "ON forecasts USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_f_transaction_time "
        "ON forecasts USING gist (transaction_time)"
    )

    # --- 12. progress_entries (versionable only, linked to work_package) ---
    op.execute("""
        CREATE TABLE progress_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            progress_entry_id UUID NOT NULL,
            work_package_id UUID NOT NULL,
            progress_percentage NUMERIC(5,2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            -- EVCS versionable fields (NOT branchable)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_pe_progress_entry_id "
        "ON progress_entries (progress_entry_id)"
    )
    op.execute(
        "CREATE INDEX ix_pe_work_package_id "
        "ON progress_entries (work_package_id)"
    )
    op.execute(
        "CREATE INDEX ix_pe_current_versions "
        "ON progress_entries (progress_entry_id) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_pe_valid_time "
        "ON progress_entries USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_pe_transaction_time "
        "ON progress_entries USING gist (transaction_time)"
    )
    op.execute(
        "CREATE INDEX excl_progress_entries_overlap "
        "ON progress_entries USING gist (progress_entry_id, valid_time)"
    )

    # --- 13. cost_registrations (versionable only) ---
    op.execute("""
        CREATE TABLE cost_registrations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_registration_id UUID NOT NULL,
            cost_element_id UUID NOT NULL,
            cost_event_id UUID,
            amount NUMERIC(15,2) NOT NULL,
            quantity NUMERIC(15,2),
            unit_of_measure VARCHAR(50),
            registration_date TIMESTAMPTZ,
            description TEXT,
            invoice_number VARCHAR(100),
            vendor_reference VARCHAR(255),

            -- EVCS versionable fields (NOT branchable)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cr_cost_registration_id "
        "ON cost_registrations (cost_registration_id)"
    )
    op.execute(
        "CREATE INDEX ix_cr_cost_element_id "
        "ON cost_registrations (cost_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_cr_cost_event_id "
        "ON cost_registrations (cost_event_id)"
    )
    op.execute(
        "CREATE INDEX ix_cr_cost_element_date "
        "ON cost_registrations (cost_element_id, registration_date)"
    )
    op.execute(
        "CREATE INDEX ix_cr_created_by "
        "ON cost_registrations (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_cr_valid_time "
        "ON cost_registrations USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_cr_transaction_time "
        "ON cost_registrations USING gist (transaction_time)"
    )

    # --- 14. cost_registration_attachments (simple, non-versioned) ---
    op.execute("""
        CREATE TABLE cost_registration_attachments (
            cost_registration_id UUID NOT NULL,
            filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            content BYTEA NOT NULL,
            size INTEGER NOT NULL,
            storage_key VARCHAR(512),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            id UUID PRIMARY KEY DEFAULT gen_random_uuid()
        )
    """)
    op.execute(
        "CREATE INDEX ix_cost_registration_attachments_cost_registration_id "
        "ON cost_registration_attachments (cost_registration_id)"
    )

    # ========================================================================
    # PHASE 3: RECREATE PRESERVED TABLES (same schema as before)
    # ========================================================================

    # --- branches ---
    op.execute("""
        CREATE TABLE branches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            branch_id UUID NOT NULL,
            name VARCHAR NOT NULL,
            project_id UUID NOT NULL,
            type VARCHAR NOT NULL DEFAULT 'main',
            locked BOOLEAN NOT NULL DEFAULT false,
            created_by UUID NOT NULL,
            deleted_at TIMESTAMPTZ,
            deleted_by UUID,
            branch_metadata_info JSONB,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]')
        )
    """)
    op.execute(
        "CREATE INDEX ix_branches_branch_id ON branches (branch_id)"
    )
    op.execute(
        "CREATE INDEX ix_branches_project_id ON branches (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_branches_name_project_id "
        "ON branches (name, project_id)"
    )
    op.execute(
        "CREATE INDEX ix_branches_type ON branches (type)"
    )
    op.execute(
        "CREATE INDEX ix_branches_deleted_at ON branches (deleted_at)"
    )

    # --- change_order_audit_log ---
    op.execute("""
        CREATE TABLE change_order_audit_log (
            id UUID PRIMARY KEY,
            change_order_id UUID NOT NULL,
            old_status VARCHAR NOT NULL,
            new_status VARCHAR NOT NULL,
            comment TEXT,
            changed_by UUID NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            control_date TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX ix_coal_change_order_id "
        "ON change_order_audit_log (change_order_id)"
    )
    op.execute(
        "CREATE INDEX ix_coal_changed_by "
        "ON change_order_audit_log (changed_by)"
    )
    op.execute(
        "CREATE INDEX idx_coal_control_date "
        "ON change_order_audit_log (change_order_id, control_date DESC)"
    )

    # --- change_orders ---
    op.execute("""
        CREATE TABLE change_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            change_order_id UUID NOT NULL,
            code VARCHAR NOT NULL,
            project_id UUID NOT NULL,
            title VARCHAR NOT NULL,
            description TEXT,
            justification TEXT,
            effective_date TIMESTAMPTZ,
            status VARCHAR NOT NULL DEFAULT 'Draft',

            -- EVCS versionable + branchable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR,

            -- Change order specific fields
            branch_name VARCHAR,
            impact_level VARCHAR,
            assigned_approver_id UUID,
            sla_assigned_at TIMESTAMPTZ,
            sla_due_date TIMESTAMPTZ,
            sla_status VARCHAR,
            impact_analysis_status VARCHAR,
            impact_analysis_results JSONB,
            impact_score NUMERIC,
            config_snapshot JSONB,
            custom_field_values JSONB
        )
    """)
    op.execute(
        "CREATE INDEX ix_co_change_order_id "
        "ON change_orders (change_order_id)"
    )
    op.execute(
        "CREATE INDEX ix_co_code ON change_orders (code)"
    )
    op.execute(
        "CREATE INDEX ix_co_project_id ON change_orders (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_co_created_by ON change_orders (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_co_branch_name ON change_orders (branch_name)"
    )
    op.execute(
        "CREATE INDEX ix_co_impact_level ON change_orders (impact_level)"
    )
    op.execute(
        "CREATE INDEX ix_co_sla_due_date ON change_orders (sla_due_date)"
    )

    # --- co_workflow_config ---
    op.execute("""
        CREATE TABLE co_workflow_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            project_id UUID UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT true,
            version INTEGER NOT NULL DEFAULT 1,
            created_by UUID NOT NULL,
            updated_by UUID,
            impact_weights JSONB NOT NULL,
            score_boundaries JSONB NOT NULL,
            workflow_transitions JSONB,
            holiday_country_code VARCHAR DEFAULT 'IT',
            custom_fields JSONB
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_cwc_config_id "
        "ON co_workflow_config (config_id)"
    )
    op.execute(
        "CREATE INDEX ix_cwc_config_id "
        "ON co_workflow_config (config_id)"
    )
    op.execute(
        "CREATE INDEX ix_cwc_project_id "
        "ON co_workflow_config (project_id)"
    )

    # --- co_approval_rule_config ---
    op.execute("""
        CREATE TABLE co_approval_rule_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            impact_level_name VARCHAR NOT NULL,
            required_authority_level VARCHAR NOT NULL,
            approver_role VARCHAR NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX ix_arc_config_id "
        "ON co_approval_rule_config (config_id)"
    )

    # --- co_impact_level_config ---
    op.execute("""
        CREATE TABLE co_impact_level_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            level_name VARCHAR NOT NULL,
            level_order INTEGER NOT NULL,
            threshold_amount NUMERIC NOT NULL,
            score_threshold_min NUMERIC NOT NULL,
            score_threshold_max NUMERIC NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true
        )
    """)
    op.execute(
        "CREATE INDEX ix_ilc_config_id "
        "ON co_impact_level_config (config_id)"
    )

    # --- co_sla_rule_config ---
    op.execute("""
        CREATE TABLE co_sla_rule_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            impact_level_name VARCHAR NOT NULL,
            business_days INTEGER NOT NULL,
            escalation_trigger_pct NUMERIC
        )
    """)
    op.execute(
        "CREATE INDEX ix_src_config_id "
        "ON co_sla_rule_config (config_id)"
    )

    # --- co_config_audit_log ---
    op.execute("""
        CREATE TABLE co_config_audit_log (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            changed_by UUID NOT NULL,
            old_values JSONB,
            new_values JSONB,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX ix_cal_config_id "
        "ON co_config_audit_log (config_id)"
    )

    # --- project_budget_settings ---
    op.execute("""
        CREATE TABLE project_budget_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_budget_settings_id UUID NOT NULL,
            project_id UUID NOT NULL,
            warning_threshold_percent NUMERIC NOT NULL DEFAULT 80.0,
            allow_project_admin_override BOOLEAN NOT NULL DEFAULT true,
            enforce_budget BOOLEAN NOT NULL DEFAULT false,

            -- EVCS versionable fields
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_pbs_project_budget_settings_id "
        "ON project_budget_settings (project_budget_settings_id)"
    )
    op.execute(
        "CREATE INDEX ix_pbs_project_id "
        "ON project_budget_settings (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_pbs_created_by "
        "ON project_budget_settings (created_by)"
    )


def downgrade() -> None:
    # ========================================================================
    # Downgrade: drop new ANSI-748 tables and recreate old schema
    # ========================================================================

    # Drop new tables (dependency order)
    op.execute("DROP TABLE IF EXISTS cost_registrations CASCADE")
    op.execute("DROP TABLE IF EXISTS progress_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_events CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_elements CASCADE")
    op.execute("DROP TABLE IF EXISTS work_packages CASCADE")
    op.execute("DROP TABLE IF EXISTS control_accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS wbs_elements CASCADE")
    op.execute("DROP TABLE IF EXISTS forecasts CASCADE")
    op.execute("DROP TABLE IF EXISTS schedule_baselines CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_event_types CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_element_types CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
    op.execute("DROP TABLE IF EXISTS organizational_units CASCADE")

    # Drop preserved tables that were recreated
    op.execute("DROP TABLE IF EXISTS project_budget_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS co_config_audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS co_sla_rule_config CASCADE")
    op.execute("DROP TABLE IF EXISTS co_impact_level_config CASCADE")
    op.execute("DROP TABLE IF EXISTS co_approval_rule_config CASCADE")
    op.execute("DROP TABLE IF EXISTS co_workflow_config CASCADE")
    op.execute("DROP TABLE IF EXISTS change_orders CASCADE")
    op.execute("DROP TABLE IF EXISTS change_order_audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS branches CASCADE")

    # ========================================================================
    # Recreate OLD schema (departments, wbes, package_types, etc.)
    # ========================================================================

    # --- departments ---
    op.execute("""
        CREATE TABLE departments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            department_id UUID NOT NULL,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            manager_id UUID,
            is_active BOOLEAN NOT NULL DEFAULT true,
            description VARCHAR,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_departments_department_id "
        "ON departments (department_id)"
    )
    op.execute(
        "CREATE INDEX ix_departments_code ON departments (code)"
    )
    op.execute(
        "CREATE INDEX ix_departments_created_by "
        "ON departments (created_by)"
    )

    # --- cost_element_types ---
    op.execute("""
        CREATE TABLE cost_element_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_element_type_id UUID NOT NULL,
            department_id UUID NOT NULL,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description TEXT,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cost_element_types_cost_element_type_id "
        "ON cost_element_types (cost_element_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_element_types_department_id "
        "ON cost_element_types (department_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_element_types_code "
        "ON cost_element_types (code)"
    )
    op.execute(
        "CREATE INDEX ix_cost_element_types_valid_time "
        "ON cost_element_types USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_cost_element_types_transaction_time "
        "ON cost_element_types USING gist (transaction_time)"
    )

    # --- package_types ---
    op.execute("""
        CREATE TABLE package_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            package_type_id UUID NOT NULL,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            color VARCHAR NOT NULL,
            description TEXT,
            is_quality BOOLEAN NOT NULL DEFAULT false,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_package_types_package_type_id "
        "ON package_types (package_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_package_types_code ON package_types (code)"
    )
    op.execute(
        "CREATE INDEX ix_package_types_created_by "
        "ON package_types (created_by)"
    )

    # --- projects ---
    op.execute("""
        CREATE TABLE projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            name VARCHAR NOT NULL,
            code VARCHAR NOT NULL,
            contract_value NUMERIC,
            currency VARCHAR NOT NULL DEFAULT 'EUR',
            status VARCHAR NOT NULL,
            start_date TIMESTAMPTZ,
            end_date TIMESTAMPTZ,
            description TEXT,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR
        )
    """)
    op.execute(
        "CREATE INDEX ix_projects_project_id ON projects (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_projects_code ON projects (code)"
    )
    op.execute(
        "CREATE INDEX ix_projects_name ON projects (name)"
    )
    op.execute(
        "CREATE INDEX ix_projects_status ON projects (status)"
    )
    op.execute(
        "CREATE INDEX ix_projects_created_by ON projects (created_by)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_projects_project_id_branch_current "
        "ON projects (project_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL "
        "AND NOT isempty(valid_time)"
    )

    # --- wbes ---
    op.execute("""
        CREATE TABLE wbes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            wbe_id UUID NOT NULL,
            project_id UUID NOT NULL,
            parent_wbe_id UUID,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            level INTEGER NOT NULL,
            description TEXT,
            revenue_allocation NUMERIC,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR
        )
    """)
    op.execute(
        "CREATE INDEX ix_wbes_wbe_id ON wbes (wbe_id)"
    )
    op.execute(
        "CREATE INDEX ix_wbes_project_id ON wbes (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_wbes_parent_wbe_id ON wbes (parent_wbe_id)"
    )
    op.execute(
        "CREATE INDEX ix_wbes_code ON wbes (code)"
    )
    op.execute(
        "CREATE INDEX ix_wbes_name ON wbes (name)"
    )
    op.execute(
        "CREATE INDEX ix_wbes_level ON wbes (level)"
    )
    op.execute(
        "CREATE INDEX ix_wbes_created_by ON wbes (created_by)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_wbes_wbe_id_branch_current "
        "ON wbes (wbe_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- cost_elements (old schema: under wbe, branchable) ---
    op.execute("""
        CREATE TABLE cost_elements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_element_id UUID NOT NULL,
            wbe_id UUID NOT NULL,
            cost_element_type_id UUID NOT NULL,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            budget_amount NUMERIC NOT NULL DEFAULT 0,
            description TEXT,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR,
            schedule_baseline_id UUID,
            forecast_id UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cost_elements_cost_element_id "
        "ON cost_elements (cost_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_wbe_id ON cost_elements (wbe_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_cost_element_type_id "
        "ON cost_elements (cost_element_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_code ON cost_elements (code)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_name ON cost_elements (name)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_branch ON cost_elements (branch)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_schedule_baseline_id "
        "ON cost_elements (schedule_baseline_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_forecast_id "
        "ON cost_elements (forecast_id)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_valid_time "
        "ON cost_elements USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_transaction_time "
        "ON cost_elements USING gist (transaction_time)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_cost_elements_cost_element_id_branch_current "
        "ON cost_elements (cost_element_id, branch) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )

    # --- work_packages (old: QualityImpact) ---
    op.execute("""
        CREATE TABLE work_packages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            work_package_id UUID NOT NULL,
            external_event_id VARCHAR,
            project_id UUID NOT NULL,
            event_date TIMESTAMPTZ,
            coq_category VARCHAR,
            cost_impact NUMERIC NOT NULL DEFAULT 0,
            schedule_impact_days SMALLINT,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            name VARCHAR NOT NULL,
            description TEXT,
            status VARCHAR NOT NULL DEFAULT 'open',
            package_type_id UUID NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX ix_wp_work_package_id "
        "ON work_packages (work_package_id)"
    )
    op.execute(
        "CREATE INDEX ix_wp_external_event_id "
        "ON work_packages (external_event_id)"
    )
    op.execute(
        "CREATE INDEX ix_wp_project_id ON work_packages (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_wp_package_type_id "
        "ON work_packages (package_type_id)"
    )
    op.execute(
        "CREATE INDEX ix_wp_created_by ON work_packages (created_by)"
    )

    # --- schedule_baselines (old: linked to cost_element) ---
    op.execute("""
        CREATE TABLE schedule_baselines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            schedule_baseline_id UUID NOT NULL,
            cost_element_id UUID,
            name VARCHAR NOT NULL,
            start_date TIMESTAMPTZ NOT NULL,
            end_date TIMESTAMPTZ NOT NULL,
            progression_type VARCHAR NOT NULL DEFAULT 'LINEAR',
            description TEXT,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR
        )
    """)
    op.execute(
        "CREATE INDEX ix_sb_schedule_baseline_id "
        "ON schedule_baselines (schedule_baseline_id)"
    )
    op.execute(
        "CREATE INDEX ix_sb_cost_element_id "
        "ON schedule_baselines (cost_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_sb_name ON schedule_baselines (name)"
    )
    op.execute(
        "CREATE INDEX ix_sb_start_date ON schedule_baselines (start_date)"
    )
    op.execute(
        "CREATE INDEX ix_sb_end_date ON schedule_baselines (end_date)"
    )
    op.execute(
        "CREATE INDEX ix_sb_created_by ON schedule_baselines (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_sb_branch ON schedule_baselines (branch)"
    )
    op.execute(
        "CREATE INDEX ix_sb_valid_time "
        "ON schedule_baselines USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_sb_transaction_time "
        "ON schedule_baselines USING gist (transaction_time)"
    )

    # --- forecasts (old schema) ---
    op.execute("""
        CREATE TABLE forecasts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            forecast_id UUID NOT NULL,
            eac_amount NUMERIC NOT NULL,
            basis_of_estimate TEXT NOT NULL,
            approved_date TIMESTAMPTZ,
            approved_by UUID,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR
        )
    """)
    op.execute(
        "CREATE INDEX ix_f_forecast_id ON forecasts (forecast_id)"
    )
    op.execute(
        "CREATE INDEX ix_f_created_by ON forecasts (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_f_approved_by ON forecasts (approved_by) "
        "WHERE approved_by IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_f_branch ON forecasts (branch)"
    )
    op.execute(
        "CREATE INDEX ix_f_valid_time "
        "ON forecasts USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_f_transaction_time "
        "ON forecasts USING gist (transaction_time)"
    )

    # --- progress_entries (old: linked to cost_element_id) ---
    op.execute("""
        CREATE TABLE progress_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            progress_entry_id UUID NOT NULL,
            cost_element_id UUID NOT NULL,
            progress_percentage NUMERIC NOT NULL,
            notes TEXT,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX ix_pe_progress_entry_id "
        "ON progress_entries (progress_entry_id)"
    )
    op.execute(
        "CREATE INDEX ix_pe_cost_element_id "
        "ON progress_entries (cost_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_pe_current_versions "
        "ON progress_entries (progress_entry_id) "
        "WHERE upper(valid_time) IS NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_pe_valid_time "
        "ON progress_entries USING gist (valid_time)"
    )
    op.execute(
        "CREATE INDEX ix_pe_transaction_time "
        "ON progress_entries USING gist (transaction_time)"
    )
    op.execute(
        "CREATE INDEX excl_progress_entries_overlap "
        "ON progress_entries USING gist (progress_entry_id, valid_time)"
    )

    # --- cost_registrations (old: work_package_id instead of cost_event_id) ---
    op.execute("""
        CREATE TABLE cost_registrations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_registration_id UUID NOT NULL,
            cost_element_id UUID NOT NULL,
            amount NUMERIC NOT NULL,
            quantity NUMERIC,
            unit_of_measure VARCHAR,
            registration_date TIMESTAMPTZ,
            description TEXT,
            invoice_number VARCHAR,
            vendor_reference VARCHAR,
            work_package_id UUID,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_cr_cost_registration_id "
        "ON cost_registrations (cost_registration_id)"
    )
    op.execute(
        "CREATE INDEX ix_cr_cost_element_id "
        "ON cost_registrations (cost_element_id)"
    )
    op.execute(
        "CREATE INDEX ix_cr_work_package_id "
        "ON cost_registrations (work_package_id)"
    )
    op.execute(
        "CREATE INDEX ix_cr_cost_element_date "
        "ON cost_registrations (cost_element_id, registration_date)"
    )
    op.execute(
        "CREATE INDEX ix_cr_created_by "
        "ON cost_registrations (created_by)"
    )

    # --- branches ---
    op.execute("""
        CREATE TABLE branches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            branch_id UUID NOT NULL,
            name VARCHAR NOT NULL,
            project_id UUID NOT NULL,
            type VARCHAR NOT NULL DEFAULT 'main',
            locked BOOLEAN NOT NULL DEFAULT false,
            created_by UUID NOT NULL,
            deleted_at TIMESTAMPTZ,
            deleted_by UUID,
            branch_metadata_info JSONB,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]')
        )
    """)
    op.execute(
        "CREATE INDEX ix_branches_branch_id ON branches (branch_id)"
    )
    op.execute(
        "CREATE INDEX ix_branches_project_id ON branches (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_branches_name_project_id "
        "ON branches (name, project_id)"
    )
    op.execute(
        "CREATE INDEX ix_branches_type ON branches (type)"
    )
    op.execute(
        "CREATE INDEX ix_branches_deleted_at ON branches (deleted_at)"
    )

    # --- change_order_audit_log ---
    op.execute("""
        CREATE TABLE change_order_audit_log (
            id UUID PRIMARY KEY,
            change_order_id UUID NOT NULL,
            old_status VARCHAR NOT NULL,
            new_status VARCHAR NOT NULL,
            comment TEXT,
            changed_by UUID NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            control_date TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX ix_coal_change_order_id "
        "ON change_order_audit_log (change_order_id)"
    )
    op.execute(
        "CREATE INDEX ix_coal_changed_by "
        "ON change_order_audit_log (changed_by)"
    )
    op.execute(
        "CREATE INDEX idx_coal_control_date "
        "ON change_order_audit_log (change_order_id, control_date DESC)"
    )

    # --- change_orders ---
    op.execute("""
        CREATE TABLE change_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            change_order_id UUID NOT NULL,
            code VARCHAR NOT NULL,
            project_id UUID NOT NULL,
            title VARCHAR NOT NULL,
            description TEXT,
            justification TEXT,
            effective_date TIMESTAMPTZ,
            status VARCHAR NOT NULL DEFAULT 'Draft',
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            branch VARCHAR NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR,
            branch_name VARCHAR,
            impact_level VARCHAR,
            assigned_approver_id UUID,
            sla_assigned_at TIMESTAMPTZ,
            sla_due_date TIMESTAMPTZ,
            sla_status VARCHAR,
            impact_analysis_status VARCHAR,
            impact_analysis_results JSONB,
            impact_score NUMERIC,
            config_snapshot JSONB,
            custom_field_values JSONB
        )
    """)
    op.execute(
        "CREATE INDEX ix_co_change_order_id "
        "ON change_orders (change_order_id)"
    )
    op.execute(
        "CREATE INDEX ix_co_code ON change_orders (code)"
    )
    op.execute(
        "CREATE INDEX ix_co_project_id ON change_orders (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_co_created_by ON change_orders (created_by)"
    )
    op.execute(
        "CREATE INDEX ix_co_branch_name ON change_orders (branch_name)"
    )
    op.execute(
        "CREATE INDEX ix_co_impact_level ON change_orders (impact_level)"
    )
    op.execute(
        "CREATE INDEX ix_co_sla_due_date ON change_orders (sla_due_date)"
    )

    # --- co_workflow_config ---
    op.execute("""
        CREATE TABLE co_workflow_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            project_id UUID UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT true,
            version INTEGER NOT NULL DEFAULT 1,
            created_by UUID NOT NULL,
            updated_by UUID,
            impact_weights JSONB NOT NULL,
            score_boundaries JSONB NOT NULL,
            workflow_transitions JSONB,
            holiday_country_code VARCHAR DEFAULT 'IT',
            custom_fields JSONB
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_cwc_config_id "
        "ON co_workflow_config (config_id)"
    )
    op.execute(
        "CREATE INDEX ix_cwc_config_id "
        "ON co_workflow_config (config_id)"
    )
    op.execute(
        "CREATE INDEX ix_cwc_project_id "
        "ON co_workflow_config (project_id)"
    )

    # --- co_approval_rule_config ---
    op.execute("""
        CREATE TABLE co_approval_rule_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            impact_level_name VARCHAR NOT NULL,
            required_authority_level VARCHAR NOT NULL,
            approver_role VARCHAR NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX ix_arc_config_id "
        "ON co_approval_rule_config (config_id)"
    )

    # --- co_impact_level_config ---
    op.execute("""
        CREATE TABLE co_impact_level_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            level_name VARCHAR NOT NULL,
            level_order INTEGER NOT NULL,
            threshold_amount NUMERIC NOT NULL,
            score_threshold_min NUMERIC NOT NULL,
            score_threshold_max NUMERIC NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true
        )
    """)
    op.execute(
        "CREATE INDEX ix_ilc_config_id "
        "ON co_impact_level_config (config_id)"
    )

    # --- co_sla_rule_config ---
    op.execute("""
        CREATE TABLE co_sla_rule_config (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            impact_level_name VARCHAR NOT NULL,
            business_days INTEGER NOT NULL,
            escalation_trigger_pct NUMERIC
        )
    """)
    op.execute(
        "CREATE INDEX ix_src_config_id "
        "ON co_sla_rule_config (config_id)"
    )

    # --- co_config_audit_log ---
    op.execute("""
        CREATE TABLE co_config_audit_log (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            config_id UUID NOT NULL,
            changed_by UUID NOT NULL,
            old_values JSONB,
            new_values JSONB,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX ix_cal_config_id "
        "ON co_config_audit_log (config_id)"
    )

    # --- project_budget_settings ---
    op.execute("""
        CREATE TABLE project_budget_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_budget_settings_id UUID NOT NULL,
            project_id UUID NOT NULL,
            warning_threshold_percent NUMERIC NOT NULL DEFAULT 80.0,
            allow_project_admin_override BOOLEAN NOT NULL DEFAULT true,
            enforce_budget BOOLEAN NOT NULL DEFAULT false,
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        )
    """)
    op.execute(
        "CREATE INDEX ix_pbs_project_budget_settings_id "
        "ON project_budget_settings (project_budget_settings_id)"
    )
    op.execute(
        "CREATE INDEX ix_pbs_project_id "
        "ON project_budget_settings (project_id)"
    )
    op.execute(
        "CREATE INDEX ix_pbs_created_by "
        "ON project_budget_settings (created_by)"
    )
