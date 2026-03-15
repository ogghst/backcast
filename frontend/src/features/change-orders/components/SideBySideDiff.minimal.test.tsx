import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { SideBySideDiff } from "./SideBySideDiff";

describe("SideBySideDiff Minimal", () => {
  it("should render without crashing", () => {
    const mainData = { wbe_name: "Old Name" };
    const branchData = { wbe_name: "New Name" };
    const fieldLabels = { wbe_name: "WBE Name" };

    const { container } = render(
      <SideBySideDiff
        mainData={mainData}
        branchData={branchData}
        fieldLabels={fieldLabels}
      />
    );

    expect(container).toBeInTheDocument();
  });
});
