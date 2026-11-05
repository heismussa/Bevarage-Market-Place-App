import type { components } from "@beverage/api";

const UNIT_LABELS: Record<components["schemas"]["UnitEnum"], string> = {
  BOTTLE: "bottle",
  CAN: "can",
  CRATE: "crate",
  CARTON: "carton",
  PACK: "pack",
};

export function unitLabel(unit: string): string {
  return UNIT_LABELS[unit as keyof typeof UNIT_LABELS] ?? unit.toLowerCase();
}

/** "1.234" -> "1.2 km". Distance comes from the server. */
export function formatDistance(km: number | null | undefined): string | null {
  if (km === null || km === undefined || !Number.isFinite(km)) return null;
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

/** Payments that go through a mobile-money prompt (everything but cash). */
export function isMobileMoney(method: string | null | undefined): boolean {
  return method !== undefined && method !== null && method !== "CASH";
}
