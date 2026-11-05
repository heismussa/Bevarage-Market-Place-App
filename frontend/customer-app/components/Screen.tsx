import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import type { ReactNode } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

type ScreenProps = {
  title?: string;
  /** Show a back arrow (falls back to home when there is no history). */
  back?: boolean;
  right?: ReactNode;
  /** Wrap children in a ScrollView. Use false when children are a FlatList. */
  scroll?: boolean;
  /** Add horizontal padding around children. */
  padded?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  /** Sticky area under the content (e.g. primary action). */
  footer?: ReactNode;
  children: ReactNode;
};

export function Screen({
  title,
  back = false,
  right,
  scroll = true,
  padded = true,
  refreshing = false,
  onRefresh,
  footer,
  children,
}: ScreenProps) {
  const router = useRouter();

  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace("/");
  };

  return (
    <SafeAreaView edges={["top"]} className="flex-1 bg-background">
      {title || back || right ? (
        <View className="min-h-[52px] flex-row items-center px-4 pb-2 pt-1">
          {back ? (
            <Pressable
              onPress={goBack}
              hitSlop={12}
              accessibilityRole="button"
              accessibilityLabel="Go back"
              className="-ml-2 mr-1 h-10 w-10 items-center justify-center"
            >
              <Ionicons name="chevron-back" size={26} color="#FFFFFF" />
            </Pressable>
          ) : null}
          <Text
            numberOfLines={1}
            className="flex-1 text-2xl font-bold text-foreground"
          >
            {title}
          </Text>
          {right}
        </View>
      ) : null}

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {scroll ? (
          <ScrollView
            className="flex-1"
            contentContainerStyle={{
              paddingHorizontal: padded ? 16 : 0,
              paddingBottom: 32,
              flexGrow: 1,
            }}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
            refreshControl={
              onRefresh ? (
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  tintColor="#C1E8FF"
                />
              ) : undefined
            }
          >
            {children}
          </ScrollView>
        ) : (
          <View className="flex-1">{children}</View>
        )}
        {footer ? (
          <View className="border-t border-border bg-background px-4 pb-4 pt-3">
            {footer}
          </View>
        ) : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
