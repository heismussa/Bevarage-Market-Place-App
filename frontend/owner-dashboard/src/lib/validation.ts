import { normalizePhone } from "@beverage/api";
import { z } from "zod";

/** Tanzania phone; the API wants +255XXXXXXXXX. */
export const phoneSchema = z
  .string()
  .trim()
  .min(1, "Enter your phone number.")
  .refine((value) => normalizePhone(value) !== null, {
    message: "Enter a valid Tanzanian phone number, e.g. 0712 345 678.",
  });

export const passwordSchema = z.string().min(8, "Use at least 8 characters.");

export const decimalSchema = (label: string) =>
  z
    .string()
    .trim()
    .min(1, `${label} is required.`)
    .regex(/^\d+(\.\d{1,2})?$/, `${label} must be a number, e.g. 1500 or 1500.50.`);

export const optionalDecimalCoord = (label: string) =>
  z
    .string()
    .trim()
    .refine((value) => value === "" || /^-?\d+(\.\d+)?$/.test(value), {
      message: `${label} must be a number.`,
    });

export function phoneForApi(value: string): string {
  return normalizePhone(value) ?? value.trim();
}

/** ISO yyyy-mm-dd for a Date in the user's local calendar. */
export function toDateInput(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
