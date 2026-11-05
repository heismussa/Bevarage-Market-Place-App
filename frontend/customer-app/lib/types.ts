import type { components } from "@beverage/api";

type Schemas = components["schemas"];

export type Me = Schemas["Me"];
export type Address = Schemas["Address"];
export type AddressInput = Schemas["AddressRequest"];
export type Cart = Schemas["Cart"];
export type CartLine = Schemas["CartLine"];
export type CartWarning = Schemas["CartWarning"];
export type Category = Schemas["Category"];
export type Notification = Schemas["Notification"];
export type OrderDetail = Schemas["OrderDetail"];
export type OrderList = Schemas["OrderList"];
export type OrderStatusValue = Schemas["OrderStatusEnum"];
export type Payment = Schemas["Payment"];
export type PopularProduct = Schemas["PopularProduct"];
export type PublicProduct = Schemas["PublicProduct"];
export type PublicStore = Schemas["PublicStore"];
export type StatusHistory = Schemas["StatusHistory"];
export type CheckoutPaymentMethod = Schemas["CheckoutPaymentMethodEnum"];

/** Card shape shared by ProductCard for regular and popular products. */
export type ProductSummary = Pick<
  PublicProduct,
  | "id"
  | "store"
  | "store_name"
  | "name"
  | "image"
  | "unit"
  | "price"
  | "stock_quantity"
  | "availability_status"
  | "in_stock"
>;

export type Paginated<T> = {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
};
