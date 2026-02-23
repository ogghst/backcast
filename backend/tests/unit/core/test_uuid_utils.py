"""Tests for UUID utilities."""

import pytest

from app.core.uuid_utils import (
    generate_cost_element_type_uuid,
    generate_cost_element_uuid,
    generate_department_uuid,
    generate_entity_uuid,
    generate_project_uuid,
    generate_user_uuid,
    generate_wbe_uuid,
    get_entity_namespace,
)


class TestGetEntityNamespace:
    """Tests for get_entity_namespace function."""

    def test_returns_valid_uuid_for_known_entity_types(self):
        """Should return valid UUID for all known entity types."""
        entity_types = [
            "project",
            "wbe",
            "cost_element",
            "department",
            "cost_element_type",
            "user",
        ]

        for entity_type in entity_types:
            namespace = get_entity_namespace(entity_type)
            assert isinstance(namespace, str) or hasattr(namespace, "hex")
            # UUID should be deterministic
            assert namespace == get_entity_namespace(entity_type)

    def test_raises_for_unknown_entity_type(self):
        """Should raise ValueError for unknown entity types."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            get_entity_namespace("unknown_entity")

    def test_namespaces_are_different_per_entity_type(self):
        """Should generate different namespaces for different entity types."""
        project_ns = get_entity_namespace("project")
        wbe_ns = get_entity_namespace("wbe")
        user_ns = get_entity_namespace("user")

        assert project_ns != wbe_ns
        assert project_ns != user_ns
        assert wbe_ns != user_ns


class TestGenerateEntityUuid:
    """Tests for generate_entity_uuid function."""

    def test_returns_valid_uuid(self):
        """Should return a valid UUID object."""
        result = generate_entity_uuid("project", "TEST-001")
        assert hasattr(result, "hex")
        assert len(str(result)) == 36  # Standard UUID string length

    def test_deterministic_same_inputs(self):
        """Should return same UUID for same inputs."""
        uuid1 = generate_entity_uuid("project", "PRJ-DEMO-001")
        uuid2 = generate_entity_uuid("project", "PRJ-DEMO-001")
        assert uuid1 == uuid2

    def test_different_for_different_identifiers(self):
        """Should return different UUIDs for different identifiers."""
        uuid1 = generate_entity_uuid("project", "PRJ-001")
        uuid2 = generate_entity_uuid("project", "PRJ-002")
        assert uuid1 != uuid2

    def test_different_for_different_entity_types(self):
        """Should return different UUIDs for different entity types even with same identifier."""
        project_uuid = generate_entity_uuid("project", "CODE-001")
        wbe_uuid = generate_entity_uuid("wbe", "CODE-001")
        assert project_uuid != wbe_uuid

    def test_raises_for_unknown_entity_type(self):
        """Should raise ValueError for unknown entity types."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            generate_entity_uuid("unknown", "test-id")


class TestConvenienceFunctions:
    """Tests for entity-specific UUID generation functions."""

    def test_generate_project_uuid(self):
        """Should generate deterministic UUIDs for projects."""
        uuid1 = generate_project_uuid("PRJ-DEMO-001")
        uuid2 = generate_project_uuid("PRJ-DEMO-001")
        assert uuid1 == uuid2
        assert str(uuid1) == str(uuid2)

    def test_generate_wbe_uuid(self):
        """Should generate deterministic UUIDs for WBEs."""
        uuid1 = generate_wbe_uuid("PRJ-DEMO-001-L1-1")
        uuid2 = generate_wbe_uuid("PRJ-DEMO-001-L1-1")
        assert uuid1 == uuid2

    def test_generate_cost_element_uuid(self):
        """Should generate deterministic UUIDs for cost elements."""
        uuid1 = generate_cost_element_uuid("CE-001")
        uuid2 = generate_cost_element_uuid("CE-001")
        assert uuid1 == uuid2

    def test_generate_department_uuid(self):
        """Should generate deterministic UUIDs for departments."""
        uuid1 = generate_department_uuid("ENG")
        uuid2 = generate_department_uuid("ENG")
        assert uuid1 == uuid2

    def test_generate_cost_element_type_uuid(self):
        """Should generate deterministic UUIDs for cost element types."""
        uuid1 = generate_cost_element_type_uuid("LAB")
        uuid2 = generate_cost_element_type_uuid("LAB")
        assert uuid1 == uuid2

    def test_generate_user_uuid(self):
        """Should generate deterministic UUIDs for users."""
        uuid1 = generate_user_uuid("admin@backcast.org")
        uuid2 = generate_user_uuid("admin@backcast.org")
        assert uuid1 == uuid2


class TestKnownVectors:
    """Tests against known UUID vectors to ensure consistency."""

    # Actual UUID values computed using UUIDv5 with namespace strategy
    def test_project_known_vector(self):
        """Should generate consistent UUID for known project code."""
        result = generate_project_uuid("PRJ-DEMO-001")
        # Documented value for reference
        assert str(result) == "d54fbbe6-f3df-51db-9c3e-9408700442be"

    def test_wbe_known_vector(self):
        """Should generate consistent UUID for known WBE code."""
        result = generate_wbe_uuid("PRJ-DEMO-001-L1-1")
        # Documented value for reference
        assert str(result) == "3a42f62c-96f8-5392-bff1-2e16f97734f0"

    def test_user_known_vector(self):
        """Should generate consistent UUID for known user email."""
        result = generate_user_uuid("admin@backcast.org")
        # Documented value for reference
        assert str(result) == "e03556f3-4385-5d68-a685-af307fc8af5c"


class TestNamespaceIsolation:
    """Tests to ensure UUIDs don't collide across namespaces."""

    def test_no_collision_between_entity_types(self):
        """Should not generate colliding UUIDs across different entity types."""
        test_codes = ["TEST-001", "TEST-002", "ADMIN", "user@example.com"]

        all_uuids = []
        for code in test_codes:
            all_uuids.append(generate_project_uuid(code))
            all_uuids.append(generate_wbe_uuid(code))
            all_uuids.append(generate_cost_element_uuid(code))
            all_uuids.append(generate_department_uuid(code))
            all_uuids.append(generate_cost_element_type_uuid(code))
            all_uuids.append(generate_user_uuid(code))

        # Check all UUIDs are unique
        assert len(set(all_uuids)) == len(all_uuids), "UUID collision detected!"

    def test_uuid_version_is_5(self):
        """Should generate UUIDv5 (version 5, name-based)."""
        result = generate_entity_uuid("project", "TEST")
        # UUIDv5 has version number 5 in the most significant 4 bits of byte 6
        # In string representation, this is the 14th character
        assert str(result)[14] == "5"
