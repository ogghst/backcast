"""UUID utilities for deterministic entity ID generation.

Uses UUIDv5 (namespace-based) to generate consistent UUIDs for entities
based on their type and unique identifier (code, email, etc.).

This ensures that seed data produces identical UUIDs across different runs,
making tests deterministic and relationships stable.
"""

from uuid import UUID, uuid5

# DNS namespace from RFC 4122
DNS_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Entity type identifiers
ENTITY_TYPE_PROJECT = "project"
ENTITY_TYPE_WBE = "wbe"
ENTITY_TYPE_COST_ELEMENT = "cost_element"
ENTITY_TYPE_DEPARTMENT = "department"
ENTITY_TYPE_COST_ELEMENT_TYPE = "cost_element_type"
ENTITY_TYPE_USER = "user"

# Mapping of entity types to their namespace strings
ENTITY_NAMESPACES = {
    ENTITY_TYPE_PROJECT: "backcast.org.project",
    ENTITY_TYPE_WBE: "backcast.org.wbe",
    ENTITY_TYPE_COST_ELEMENT: "backcast.org.cost_element",
    ENTITY_TYPE_DEPARTMENT: "backcast.org.department",
    ENTITY_TYPE_COST_ELEMENT_TYPE: "backcast.org.cost_element_type",
    ENTITY_TYPE_USER: "backcast.org.user",
}


def get_entity_namespace(entity_type: str) -> UUID:
    """Get the namespace UUID for a given entity type.

    Args:
        entity_type: The entity type (e.g., "project", "wbe", "user")

    Returns:
        UUIDv5 namespace for the entity type

    Raises:
        ValueError: If entity_type is not recognized
    """
    if entity_type not in ENTITY_NAMESPACES:
        raise ValueError(
            f"Unknown entity type: {entity_type}. "
            f"Valid types: {list(ENTITY_NAMESPACES.keys())}"
        )

    namespace_str = ENTITY_NAMESPACES[entity_type]
    return uuid5(DNS_NAMESPACE, namespace_str)


def generate_entity_uuid(entity_type: str, identifier: str) -> UUID:
    """Generate a deterministic UUID for an entity.

    The UUID is generated using UUIDv5 with:
    - Namespace: UUIDv5(DNS, "backcast.org.{entity_type}")
    - Name: The entity's unique identifier (code, email, etc.)

    This ensures that the same entity always gets the same UUID,
    making seeding deterministic.

    Args:
        entity_type: The entity type (e.g., "project", "wbe", "user")
        identifier: The entity's unique identifier (code, email, etc.)

    Returns:
        Deterministic UUIDv5 for the entity

    Raises:
        ValueError: If entity_type is not recognized

    Examples:
        >>> generate_entity_uuid("project", "PRJ-DEMO-001")
        UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890')

        >>> generate_entity_uuid("user", "admin@backcast.org")
        UUID('f1e2d3c4-b5a6-9876-5432-10fedcba9876')

        >>> # Same inputs always produce same UUID
        >>> generate_entity_uuid("project", "PRJ-DEMO-001") == generate_entity_uuid("project", "PRJ-DEMO-001")
        True
    """
    namespace = get_entity_namespace(entity_type)
    return uuid5(namespace, identifier)


def generate_project_uuid(project_code: str) -> UUID:
    """Generate UUID for a Project entity.

    Args:
        project_code: Unique project code

    Returns:
        Deterministic UUID for the project
    """
    return generate_entity_uuid(ENTITY_TYPE_PROJECT, project_code)


def generate_wbe_uuid(wbe_code: str) -> UUID:
    """Generate UUID for a WBE entity.

    Args:
        wbe_code: Unique WBE code

    Returns:
        Deterministic UUID for the WBE
    """
    return generate_entity_uuid(ENTITY_TYPE_WBE, wbe_code)


def generate_cost_element_uuid(cost_element_code: str) -> UUID:
    """Generate UUID for a CostElement entity.

    Args:
        cost_element_code: Unique cost element code

    Returns:
        Deterministic UUID for the cost element
    """
    return generate_entity_uuid(ENTITY_TYPE_COST_ELEMENT, cost_element_code)


def generate_department_uuid(department_code: str) -> UUID:
    """Generate UUID for a Department entity.

    Args:
        department_code: Unique department code

    Returns:
        Deterministic UUID for the department
    """
    return generate_entity_uuid(ENTITY_TYPE_DEPARTMENT, department_code)


def generate_cost_element_type_uuid(type_code: str) -> UUID:
    """Generate UUID for a CostElementType entity.

    Args:
        type_code: Unique cost element type code

    Returns:
        Deterministic UUID for the cost element type
    """
    return generate_entity_uuid(ENTITY_TYPE_COST_ELEMENT_TYPE, type_code)


def generate_user_uuid(email: str) -> UUID:
    """Generate UUID for a User entity.

    Args:
        email: Unique user email

    Returns:
        Deterministic UUID for the user
    """
    return generate_entity_uuid(ENTITY_TYPE_USER, email)
