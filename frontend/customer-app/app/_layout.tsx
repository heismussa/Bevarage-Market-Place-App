import "../global.css";

import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#0B1220" },
          headerTintColor: "#F5F7FB",
          contentStyle: { backgroundColor: "#0B1220" },
        }}
      >
        <Stack.Screen name="index" options={{ title: "BeverageMart" }} />
      </Stack>
    </>
  );
}
