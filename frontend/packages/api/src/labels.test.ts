import { describe, expect, it } from "vitest";

import {
  orderStatusLabel,
  paymentMethodLabel,
  paymentStatusLabel,
} from "./labels";

describe("orderStatusLabel", () => {
  it("maps known statuses", () => {
    expect(orderStatusLabel("PENDING")).toBe("Pending");
    expect(orderStatusLabel("COMPLETED")).toBe("Completed");
  });
});

describe("paymentStatusLabel", () => {
  it("uses cash and mobile wording from the handoff", () => {
    expect(paymentStatusLabel("PENDING", { isCash: true })).toBe(
      "Pay on delivery",
    );
    expect(paymentStatusLabel("PENDING", { isCash: false })).toBe(
      "Not paid yet",
    );
    expect(paymentStatusLabel("CANCELLED")).toBe("Not charged");
    expect(paymentStatusLabel("PROCESSING")).toBe(
      "Waiting for approval on your phone",
    );
    expect(paymentStatusLabel("SUCCESS")).toBe("Paid");
  });
});

describe("paymentMethodLabel", () => {
  it("maps checkout methods", () => {
    expect(paymentMethodLabel("MPESA")).toBe("M-Pesa");
    expect(paymentMethodLabel("CASH")).toBe("Cash");
  });
});
