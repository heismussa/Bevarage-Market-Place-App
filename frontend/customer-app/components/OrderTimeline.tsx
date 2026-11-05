import { HIDDEN_ORDER_STATUSES, formatDateTime, orderStatusLabel } from "@beverage/api";
import { Text, View } from "react-native";

import type { StatusHistory } from "@/lib/types";

const hidden: readonly string[] = HIDDEN_ORDER_STATUSES;

/** Status timeline straight from `status_history`; newest step is highlighted. */
export function OrderTimeline({ history }: { history: StatusHistory[] }) {
  const steps = [...history]
    .filter((step) => !hidden.includes(step.status))
    .sort((a, b) => new Date(a.changed_at).getTime() - new Date(b.changed_at).getTime());

  if (steps.length === 0) return null;

  return (
    <View>
      {steps.map((step, index) => {
        const current = index === steps.length - 1;
        const last = current;
        return (
          <View key={`${step.status}-${step.changed_at}`} className="flex-row">
            <View className="mr-3 items-center">
              <View
                className={`h-3.5 w-3.5 rounded-full ${current ? "bg-primary" : "bg-border"}`}
              />
              {!last ? <View className="w-0.5 flex-1 bg-border" /> : null}
            </View>
            <View className="flex-1 pb-4">
              <Text
                className={`text-sm font-semibold ${current ? "text-primary" : "text-foreground"}`}
              >
                {orderStatusLabel(step.status)}
              </Text>
              <Text className="text-xs text-muted">{formatDateTime(step.changed_at)}</Text>
              {step.notes ? (
                <Text className="mt-0.5 text-xs text-muted">{step.notes}</Text>
              ) : null}
            </View>
          </View>
        );
      })}
    </View>
  );
}
