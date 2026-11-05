import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

type ToastKind = "success" | "error" | "info";
type ToastState = { id: number; message: string; kind: ToastKind } | null;

type ToastContextValue = {
  show: (message: string, kind?: ToastKind) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState>(null);
  const counter = useRef(0);
  const insets = useSafeAreaInsets();

  const show = useCallback((message: string, kind: ToastKind = "info") => {
    counter.current += 1;
    setToast({ id: counter.current, message, kind });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const handle = setTimeout(() => setToast(null), 3_000);
    return () => clearTimeout(handle);
  }, [toast]);

  const value = useMemo(() => ({ show }), [show]);

  const tone =
    toast?.kind === "error"
      ? "border-danger"
      : toast?.kind === "success"
        ? "border-success"
        : "border-border";

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast ? (
        <View
          pointerEvents="none"
          style={{ position: "absolute", left: 16, right: 16, top: insets.top + 8 }}
        >
          <View className={`rounded-xl border bg-surface px-4 py-3 ${tone}`}>
            <Text className="text-sm text-foreground">{toast.message}</Text>
          </View>
        </View>
      ) : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
