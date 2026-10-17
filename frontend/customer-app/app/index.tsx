import {
  formatMoney,
  normalizePhone,
  orderStatusLabel,
  paymentStatusLabel,
} from "@beverage/api";
import { colors } from "@beverage/ui-tokens";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { api } from "@/lib/api";

export default function HomeScreen() {
  const [apiStatus, setApiStatus] = useState("Checking API…");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.GET("/api/v1/health/");
        if (!cancelled) {
          setApiStatus(data?.status ? `API: ${data.status}` : "API reachable");
        }
      } catch (error) {
        if (!cancelled) {
          setApiStatus(
            error instanceof Error
              ? `API error: ${error.message}`
              : "API unreachable. Start Docker and set EXPO_PUBLIC_API_URL.",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <View className="flex-1 bg-background px-6 py-10">
      <Text className="text-sm uppercase tracking-widest text-primary">
        Customer app
      </Text>
      <Text className="mt-3 text-3xl font-bold text-foreground">BeverageMart</Text>
      <Text className="mt-2 text-base text-muted">
        Foundation A-01 to A-10. Splash, login and shopping screens come next.
      </Text>

      <View
        className="mt-8 rounded-2xl border border-slate-700 p-4"
        style={{ backgroundColor: colors.dark.surface }}
      >
        <Text className="text-sm text-muted">{apiStatus}</Text>
        <Text className="mt-3 text-sm text-foreground">
          Money helper: {formatMoney("1500.00")}
        </Text>
        <Text className="mt-1 text-sm text-foreground">
          Phone helper: {normalizePhone("0712345678")}
        </Text>
        <Text className="mt-1 text-sm text-foreground">
          Order: {orderStatusLabel("PENDING")} · Payment:{" "}
          {paymentStatusLabel("CANCELLED")}
        </Text>
      </View>
    </View>
  );
}
