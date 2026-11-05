/**
 * Display helpers. Money and coordinates stay as strings on the wire;
 * phones are always sent as +255XXXXXXXXX.
 */

const DAR_TZ = "Africa/Dar_es_Salaam";

/** "1500.00" -> "TSh 1,500" */
export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "TSh 0";
  }
  const amount = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(amount)) {
    return "TSh 0";
  }
  const formatted = new Intl.NumberFormat("en-TZ", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.round(amount));
  return `TSh ${formatted}`;
}

/** ISO timestamp or Date -> local Dar es Salaam display. */
export function formatDateTime(
  value: string | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = {
    dateStyle: "medium",
    timeStyle: "short",
  },
): string {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: DAR_TZ,
    ...options,
  }).format(date);
}

/** Calendar day only. */
export function formatDate(value: string | Date | null | undefined): string {
  return formatDateTime(value, { dateStyle: "medium", timeStyle: undefined });
}

/**
 * Normalise Tanzania phone input to +255XXXXXXXXX.
 * Accepts 0712..., 712..., +255712..., 255712...
 * Returns null when the number cannot be normalised.
 */
export function normalizePhone(raw: string): string | null {
  const digits = raw.replace(/[^\d+]/g, "").trim();
  let national = digits;

  if (national.startsWith("+")) {
    national = national.slice(1);
  }
  if (national.startsWith("255")) {
    national = national.slice(3);
  } else if (national.startsWith("0")) {
    national = national.slice(1);
  }

  if (!/^\d{9}$/.test(national)) {
    return null;
  }
  return `+255${national}`;
}

/** Soft mask for display: +255 712 345 678 */
export function formatPhoneDisplay(phone: string): string {
  const normalized = normalizePhone(phone) ?? phone;
  const match = normalized.match(/^\+255(\d{3})(\d{3})(\d{3})$/);
  if (!match) return normalized;
  return `+255 ${match[1]} ${match[2]} ${match[3]}`;
}
