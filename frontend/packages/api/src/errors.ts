/**
 * Map the backend's single error shape onto forms and toasts.
 * Body: { "error": { "code", "message", "details" } }
 */

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, string[] | string | unknown>;
  };
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, string[] | string | unknown>;

  constructor(
    code: string,
    message: string,
    status: number,
    details: Record<string, string[] | string | unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (!value || typeof value !== "object") return false;
  const error = (value as { error?: unknown }).error;
  if (!error || typeof error !== "object") return false;
  const body = error as { code?: unknown; message?: unknown };
  return typeof body.code === "string" && typeof body.message === "string";
}

export function parseApiError(status: number, body: unknown): ApiError {
  if (isApiErrorBody(body)) {
    return new ApiError(
      body.error.code,
      body.error.message,
      status,
      (body.error.details as Record<string, string[] | string | unknown>) ?? {},
    );
  }
  return new ApiError(
    "INTERNAL_ERROR",
    "Something went wrong. Please try again.",
    status,
  );
}

/** Flatten details into field -> first message, for react-hook-form setError. */
export function fieldErrors(
  error: ApiError | ApiErrorBody["error"] | Record<string, unknown>,
): Record<string, string> {
  const details =
    error instanceof ApiError
      ? error.details
      : "details" in error && error.details && typeof error.details === "object"
        ? (error.details as Record<string, unknown>)
        : {};

  const fields: Record<string, string> = {};
  for (const [key, value] of Object.entries(details)) {
    if (Array.isArray(value) && value.length > 0) {
      fields[key] = String(value[0]);
    } else if (typeof value === "string" && value) {
      fields[key] = value;
    }
  }
  return fields;
}

/** Short user-facing copy for stable error codes (handoff section 2). */
export function messageForCode(code: string, fallback?: string): string {
  const map: Record<string, string> = {
    AUTHENTICATION_FAILED: "Wrong phone number or password.",
    NOT_AUTHENTICATED: "Please log in again.",
    TOKEN_INVALID: "Your session expired. Please log in again.",
    PERMISSION_DENIED: "You do not have permission to do that.",
    NOT_FOUND: "That item is gone or is not yours.",
    VALIDATION_ERROR: "Please check the highlighted fields.",
    THROTTLED: "Too many attempts. Please wait and try again.",
    CART_STORE_CONFLICT: "Your cart has items from another store.",
    PRODUCT_UNAVAILABLE: "That product is no longer available.",
    STORE_CLOSED: "This store is closed right now.",
    INSUFFICIENT_STOCK: "Not enough stock for that quantity.",
    EMPTY_CART: "Your cart is empty.",
    INVALID_TRANSITION: "That action is not allowed for this order now.",
    PAYMENT_NOT_ALLOWED: "Payment is not available for this order.",
    PAYMENT_IN_PROGRESS: "A payment is already in progress.",
  };
  return map[code] ?? fallback ?? "Something went wrong. Please try again.";
}

/**
 * Apply field errors onto a react-hook-form-like setter.
 * setError("phone", { message: "..." })
 */
export function applyFieldErrors(
  error: ApiError,
  setError: (name: string, error: { type: string; message: string }) => void,
): void {
  const fields = fieldErrors(error);
  for (const [name, message] of Object.entries(fields)) {
    setError(name, { type: "server", message });
  }
}
