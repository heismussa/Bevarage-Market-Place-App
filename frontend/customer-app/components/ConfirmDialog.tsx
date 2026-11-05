import type { ReactNode } from "react";
import { Modal, Pressable, Text, View } from "react-native";

import { Button } from "./Button";

type ConfirmDialogProps = {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
};

export function ConfirmDialog({
  visible,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
  onConfirm,
  onCancel,
  children,
}: ConfirmDialogProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable
        onPress={onCancel}
        className="flex-1 items-center justify-center bg-black/60 px-6"
      >
        <Pressable className="w-full max-w-md rounded-2xl border border-border bg-surface p-5">
          <Text className="text-lg font-bold text-foreground">{title}</Text>
          <Text className="mt-2 text-sm text-muted">{message}</Text>
          {children}
          <View className="mt-5 flex-row gap-3">
            <Button
              title={cancelLabel}
              variant="secondary"
              className="flex-1"
              onPress={onCancel}
              disabled={loading}
            />
            <Button
              title={confirmLabel}
              variant={destructive ? "danger" : "primary"}
              className="flex-1"
              onPress={onConfirm}
              loading={loading}
            />
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
