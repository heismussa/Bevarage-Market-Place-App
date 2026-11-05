import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import type { ComponentProps } from "react";

import { useCartCount } from "@/lib/cart";

type IconName = ComponentProps<typeof Ionicons>["name"];

function tabIcon(name: IconName, focusedName: IconName) {
  return function TabIcon({ color, size, focused }: { color: string; size: number; focused: boolean }) {
    return <Ionicons name={focused ? focusedName : name} size={size} color={color} />;
  };
}

/** Screens that live inside the (app) group but are not tabs. */
const HIDDEN_SCREENS = [
  "store/[id]",
  "product/[id]",
  "checkout",
  "order/[id]",
  "notifications",
  "profile/edit",
  "profile/change-password",
  "profile/addresses",
  "profile/address-form",
] as const;

export default function AppLayout() {
  const cartCount = useCartCount();

  return (
    <Tabs
      backBehavior="history"
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#C1E8FF",
        tabBarInactiveTintColor: "#7DA0CA",
        tabBarStyle: { backgroundColor: "#052659", borderTopColor: "#173B65" },
        sceneStyle: { backgroundColor: "#021024" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: "Home", tabBarIcon: tabIcon("home-outline", "home") }}
      />
      <Tabs.Screen
        name="orders/index"
        options={{ title: "Orders", tabBarIcon: tabIcon("receipt-outline", "receipt") }}
      />
      <Tabs.Screen
        name="cart"
        options={{
          title: "Cart",
          tabBarIcon: tabIcon("cart-outline", "cart"),
          tabBarBadge: cartCount > 0 ? cartCount : undefined,
          tabBarBadgeStyle: { backgroundColor: "#C1E8FF", color: "#021024" },
        }}
      />
      <Tabs.Screen
        name="profile/index"
        options={{ title: "Profile", tabBarIcon: tabIcon("person-outline", "person") }}
      />
      {HIDDEN_SCREENS.map((name) => (
        <Tabs.Screen
          key={name}
          name={name}
          options={{
            href: null,
            tabBarStyle:
              name === "checkout"
                ? { display: "none" }
                : { backgroundColor: "#052659", borderTopColor: "#173B65" },
          }}
        />
      ))}
    </Tabs>
  );
}
