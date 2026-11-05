import { ApiError, messageForCode } from "@beverage/api";

/** Short user-facing text for any thrown value (ApiError, network failure, etc.). */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return messageForCode(error.code, error.message);
  }
  if (error instanceof TypeError) {
    return "Can't reach the server. Check your connection and try again.";
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

export function isApiError(error: unknown, code?: string): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code);
}
