import { ApiError, applyFieldErrors } from "@beverage/api";
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { errorMessage } from "./errors";

/**
 * Push server field errors onto react-hook-form. Returns a banner message when
 * the error is not attached to any known field (or is not a field error).
 */
export function applyServerError<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly string[],
): string | null {
  if (!(error instanceof ApiError)) {
    return errorMessage(error);
  }
  let applied = 0;
  applyFieldErrors(error, (name, fieldError) => {
    if (fields.includes(name)) {
      setError(name as Path<T>, fieldError);
      applied += 1;
    }
  });
  if (applied > 0 && error.code === "VALIDATION_ERROR") {
    return null;
  }
  return errorMessage(error);
}
