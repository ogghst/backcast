import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EntityMetadataCard } from "./EntityMetadataCard";

/**
 * Tests for EntityMetadataCard — the standardized entity metadata footer.
 *
 * EntityInfoCard defaults to collapsed (children unmounted), so each test
 * expands the card by clicking the "Details" header before asserting on rows.
 * jsdom has no layout, so we assert on text/label content only.
 */

const expandCard = () => {
  fireEvent.click(screen.getByText("Details"));
};

describe("EntityMetadataCard", () => {
  it("renders the 6 standard rows when all props are provided", () => {
    render(
      <EntityMetadataCard
        entityId="abc-123"
        entityIdLabel="Work Package ID"
        parentId="ca-456"
        parentLabel="Control Account"
        parentValue="Assembly CA"
        createdAt="2026-06-23T22:24:17Z"
        updatedAt="2026-06-24T05:50:39Z"
        createdBy="alice"
        validTime={{
          lower: "2026-06-23T22:24:17Z",
          upper: null,
          is_currently_valid: true,
        }}
        cardId="wp-metadata-card"
      />,
    );

    expandCard();

    // Own ID (copyable code renders the id twice: text + tooltip copy button)
    expect(screen.getAllByText("abc-123").length).toBeGreaterThan(0);
    expect(screen.getByText("Work Package ID")).toBeInTheDocument();

    // Parent
    expect(screen.getByText("Control Account")).toBeInTheDocument();
    expect(screen.getByText("Assembly CA")).toBeInTheDocument();

    // Created + Last Updated (label nodes)
    expect(screen.getByText("Created")).toBeInTheDocument();
    expect(screen.getByText("Last Updated")).toBeInTheDocument();

    // Created By
    expect(screen.getByText("Created By")).toBeInTheDocument();
    expect(screen.getByText("alice")).toBeInTheDocument();

    // Valid Time
    expect(screen.getByText("Valid Time")).toBeInTheDocument();
  });

  it("omits the Parent row when parentId is null (Project)", () => {
    render(
      <EntityMetadataCard
        entityId="proj-1"
        entityIdLabel="Project ID"
        parentId={null}
        parentLabel="Parent"
        createdAt="2026-06-23T22:24:17Z"
        updatedAt="2026-06-24T05:50:39Z"
        createdBy={null}
      />,
    );

    expandCard();

    // Own ID present, Parent label absent
    expect(screen.getAllByText("proj-1").length).toBeGreaterThan(0);
    expect(screen.queryByText("Parent")).not.toBeInTheDocument();

    // Null createdBy falls back to "System"
    expect(screen.getByText("System")).toBeInTheDocument();
  });

  it("omits the Valid Time row when validTime is not provided", () => {
    render(
      <EntityMetadataCard
        entityId="ce-1"
        entityIdLabel="Cost Element ID"
        createdAt="2026-06-23T22:24:17Z"
        updatedAt={null}
      />,
    );

    expandCard();

    expect(screen.queryByText("Valid Time")).not.toBeInTheDocument();
    // Null updatedAt renders "-"
    expect(screen.getByText("Last Updated")).toBeInTheDocument();
  });

  it("renders a read-only Custom Fields section when definitions are present", () => {
    render(
      <EntityMetadataCard
        entityId="proj-1"
        entityIdLabel="Project ID"
        createdAt="2026-06-23T22:24:17Z"
        updatedAt="2026-06-24T05:50:39Z"
        customFieldDefinitions={{
          sponsor: { type: "text", label: "Sponsor" },
          active: { type: "boolean", label: "Active" },
        }}
        customFields={{ sponsor: "Acme Corp", active: true }}
      />,
    );

    expandCard();

    expect(screen.getByText("Custom Fields")).toBeInTheDocument();
    // Field labels + stored values render via CustomFieldsRenderer readOnly.
    expect(screen.getByText("Sponsor")).toBeInTheDocument();
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Yes")).toBeInTheDocument();
  });

  it("omits the Custom Fields section when definitions are null/empty", () => {
    const { rerender } = render(
      <EntityMetadataCard
        entityId="proj-1"
        entityIdLabel="Project ID"
        createdAt="2026-06-23T22:24:17Z"
        updatedAt="2026-06-24T05:50:39Z"
        customFieldDefinitions={null}
        customFields={{ sponsor: "Acme Corp" }}
      />,
    );

    expandCard();
    expect(screen.queryByText("Custom Fields")).not.toBeInTheDocument();

    // Empty definitions object also yields no section.
    rerender(
      <EntityMetadataCard
        entityId="proj-1"
        entityIdLabel="Project ID"
        createdAt="2026-06-23T22:24:17Z"
        updatedAt="2026-06-24T05:50:39Z"
        customFieldDefinitions={{}}
      />,
    );
    expandCard();
    expect(screen.queryByText("Custom Fields")).not.toBeInTheDocument();
  });
});
