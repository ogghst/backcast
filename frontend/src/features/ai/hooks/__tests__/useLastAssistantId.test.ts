import { renderHook, act } from "@testing-library/react";
import { useLastAssistantId } from "../useLastAssistantId";

describe("useLastAssistantId", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should initialize with undefined when localStorage is empty", () => {
    const { result } = renderHook(() => useLastAssistantId());

    expect(result.current.lastAssistantId).toBeUndefined();
  });

  it("should initialize with value from localStorage", () => {
    localStorage.setItem("ai_last_selected_assistant", "assistant-123");

    const { result } = renderHook(() => useLastAssistantId());

    expect(result.current.lastAssistantId).toBe("assistant-123");
  });

  it("should save to localStorage when value changes", () => {
    const { result } = renderHook(() => useLastAssistantId());

    act(() => {
      result.current.setLastAssistantId("assistant-456");
    });

    expect(result.current.lastAssistantId).toBe("assistant-456");
    expect(localStorage.getItem("ai_last_selected_assistant")).toBe("assistant-456");
  });

  it("should remove from localStorage when set to undefined", () => {
    localStorage.setItem("ai_last_selected_assistant", "assistant-123");

    const { result } = renderHook(() => useLastAssistantId());

    act(() => {
      result.current.setLastAssistantId(undefined);
    });

    expect(result.current.lastAssistantId).toBeUndefined();
    expect(localStorage.getItem("ai_last_selected_assistant")).toBeNull();
  });
});
