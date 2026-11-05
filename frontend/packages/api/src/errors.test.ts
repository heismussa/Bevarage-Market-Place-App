import { describe, expect, it } from "vitest";

import {
  ApiError,
  applyFieldErrors,
  fieldErrors,
  messageForCode,
  parseApiError,
} from "./errors";

describe("parseApiError", () => {
  it("reads the backend error envelope", () => {
    const error = parseApiError(400, {
      error: {
        code: "VALIDATION_ERROR",
        message: "Enter a valid phone number.",
        details: { phone: ["Enter a valid phone number."] },
      },
    });
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.message).toBe("Enter a valid phone number.");
    expect(fieldErrors(error)).toEqual({
      phone: "Enter a valid phone number.",
    });
  });
});

describe("applyFieldErrors", () => {
  it("calls setError for each field", () => {
    const calls: Array<[string, string]> = [];
    const error = new ApiError("VALIDATION_ERROR", "Invalid", 400, {
      phone: ["Taken"],
      password: ["Too short"],
    });
    applyFieldErrors(error, (name, err) => {
      calls.push([name, err.message]);
    });
    expect(calls).toEqual([
      ["phone", "Taken"],
      ["password", "Too short"],
    ]);
  });
});

describe("messageForCode", () => {
  it("maps stable codes", () => {
    expect(messageForCode("AUTHENTICATION_FAILED")).toBe(
      "Wrong phone number or password.",
    );
    expect(messageForCode("TOKEN_INVALID")).toMatch(/session expired/i);
  });
});
