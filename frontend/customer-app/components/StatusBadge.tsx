import { orderStatusLabel, paymentStatusLabel } from "@beverage/api";
import { Text, View } from "react-native";

type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const toneStyles: Record<Tone, { box: string; text: string }> = {
  success: { box: "bg-success/15", text: "text-success" },
  warning: { box: "bg-warning/15", text: "text-warning" },
  danger: { box: "bg-danger/15", text: "text-danger" },
  info: { box: "bg-secondary/15", text: "text-secondary" },
  neutral: { box: "bg-border", text: "text-muted" },
};

function orderTone(status: string): Tone {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "PENDING":
      return "warning";
    case "REJECTED":
    case "CANCELLED":
      return "danger";
    case "ACCEPTED":
    case "PREPARING":
    case "READY":
    case "ASSIGNED":
    case "OUT_FOR_DELIVERY":
      return "info";
    default:
      return "neutral";
  }
}

function paymentTone(status: string): Tone {
  switch (status) {
    case "SUCCESS":
      return "success";
    case "PENDING":
    case "PROCESSING":
      return "warning";
    case "FAILED":
      return "danger";
    default:
      return "neutral";
  }
}

export function Badge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  const style = toneStyles[tone];
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${style.box}`}>
      <Text className={`text-xs font-semibold ${style.text}`}>{label}</Text>
    </View>
  );
}

export function OrderStatusBadge({ status }: { status: string }) {
  return <Badge label={orderStatusLabel(status)} tone={orderTone(status)} />;
}

export function PaymentStatusBadge({
  status,
  isCash,
}: {
  status: string;
  isCash: boolean;
}) {
  return (
    <Badge label={paymentStatusLabel(status, { isCash })} tone={paymentTone(status)} />
  );
}
