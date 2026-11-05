import type { components } from "@beverage/api";

type S = components["schemas"];

export type Me = S["Me"];
export type TokenPair = S["TokenPair"];
export type OwnerStore = S["OwnerStore"];
export type OwnerProduct = S["OwnerProduct"];
export type OwnerOrderList = S["OwnerOrderList"];
export type OwnerOrderDetail = S["OwnerOrderDetail"];
export type Dashboard = S["Dashboard"];
export type Analytics = S["Analytics"];
export type Notification = S["Notification"];
export type Category = S["Category"];
export type OrderAction = S["OrderActionEnum"];
export type OrderStatusValue = S["OrderStatusEnum"];
export type PaymentStatusValue = S["PaymentStatusEnum"];
export type PaymentMethodShare = S["PaymentMethodShare"];
export type PeriodComparison = S["PeriodComparison"];
export type DailySales = S["DailySales"];
export type TopProduct = S["TopProduct"];
export type LowStockItem = S["LowStockItem"];
export type UnitValue = S["UnitEnum"];
export type AvailabilityValue = S["AvailabilityStatusEnum"];
export type StoreStatus = S["StoreStatusEnum"];

export type Paginated<T> = {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
};

export const UNITS: { value: UnitValue; label: string }[] = [
  { value: "BOTTLE", label: "Bottle" },
  { value: "CAN", label: "Can" },
  { value: "CRATE", label: "Crate" },
  { value: "CARTON", label: "Carton" },
  { value: "PACK", label: "Pack" },
];

export const AVAILABILITY_LABELS: Record<AvailabilityValue, string> = {
  AVAILABLE: "Available",
  OUT_OF_STOCK: "Out of stock",
  UNAVAILABLE: "Unavailable",
};

export const NOTIFICATION_PAGE_SIZE = 10;
