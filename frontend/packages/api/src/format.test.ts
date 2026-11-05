import { describe, expect, it } from "vitest";

import {
  formatDateTime,
  formatMoney,
  formatPhoneDisplay,
  normalizePhone,
} from "./format";

describe("formatMoney", () => {
  it("formats server decimal strings as TSh", () => {
    expect(formatMoney("1500.00")).toBe("TSh 1,500");
    expect(formatMoney("6500.00")).toBe("TSh 6,500");
    expect(formatMoney(0)).toBe("TSh 0");
  });

  it("handles empty values", () => {
    expect(formatMoney(null)).toBe("TSh 0");
    expect(formatMoney(undefined)).toBe("TSh 0");
    expect(formatMoney("")).toBe("TSh 0");
  });
});

describe("normalizePhone", () => {
  it("accepts common Tanzania formats", () => {
    expect(normalizePhone("+255712345678")).toBe("+255712345678");
    expect(normalizePhone("255712345678")).toBe("+255712345678");
    expect(normalizePhone("0712345678")).toBe("+255712345678");
    expect(normalizePhone("712345678")).toBe("+255712345678");
    expect(normalizePhone("0712 345 678")).toBe("+255712345678");
  });

  it("rejects invalid numbers", () => {
    expect(normalizePhone("123")).toBeNull();
    expect(normalizePhone("+254712345678")).toBeNull();
    expect(normalizePhone("")).toBeNull();
  });
});

describe("formatPhoneDisplay", () => {
  it("groups digits for display", () => {
    expect(formatPhoneDisplay("+255712345678")).toBe("+255 712 345 678");
  });
});

describe("formatDateTime", () => {
  it("formats in Africa/Dar_es_Salaam", () => {
    const formatted = formatDateTime("2026-10-08T14:50:49.008237+03:00");
    expect(formatted).toMatch(/2026/);
    expect(formatted.length).toBeGreaterThan(0);
  });
});
