import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { SideBySideDiff } from "./SideBySideDiff";

describe("SideBySideDiff Minimal", () => {
  it("should render without crashing", () => {
    const mainData = { wbs_element_name: "Old Name" };
    const branchData = { wbs_element_name: "New Name" };
    const fieldLabels = { wbs_element_name: "WBE Name" };

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
