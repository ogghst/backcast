interface ValidationError {
  loc?: string[];
  msg?: string;
  type?: string;
}

interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string | ValidationError[];
    };
  };
  body?: {
    detail?: string | ValidationError[];
  };
  message?: string;
}

export const getErrorMessage = (error: unknown): string => {
  if (!error || typeof error !== "object") {
    return "An unexpected error occurred";
  }

  const err = error as ApiErrorResponse;
  // Try to find the error message in various common locations
  // 1. response.data.detail (Axios / FastAPI standard)
  // 2. body.detail (some generated clients)
  // 3. message (standard Error)
  const backendMessage =
    err.response?.data?.detail || err.body?.detail || err.message;

  // Handle Pydantic validation errors (array of objects)
  // Example: [{ loc: ["body", "password"], msg: "field required", type: "value_error.missing" }]
  if (Array.isArray(backendMessage)) {
    return backendMessage
      .map((item: ValidationError) => {
        if (typeof item === "object" && item.msg) {
          // Add field name if available (from loc)
          const field =
            item.loc && Array.isArray(item.loc)
              ? item.loc[item.loc.length - 1]
              : null;
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }

  if (typeof backendMessage === "string") {
    return backendMessage;
  }

  if (typeof backendMessage === "object") {
    return JSON.stringify(backendMessage);
  }

  return err.message || "An unexpected error occurred";
};
