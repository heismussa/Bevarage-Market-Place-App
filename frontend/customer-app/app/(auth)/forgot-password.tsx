import { normalizePhone } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Text } from "react-native";

import { Button } from "@/components/Button";
import { FormInput } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { Banner } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { applyServerError } from "@/lib/forms";
import {
  resetConfirmSchema,
  resetRequestSchema,
  type ResetConfirmForm,
  type ResetRequestForm,
} from "@/lib/validation";

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [phone, setPhone] = useState<string | null>(null);
  const [rawPhone, setRawPhone] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const requestForm = useForm<ResetRequestForm>({
    resolver: zodResolver(resetRequestSchema),
    defaultValues: { phone: "" },
  });

  const confirmForm = useForm<ResetConfirmForm>({
    resolver: zodResolver(resetConfirmSchema),
    defaultValues: { code: "", new_password: "", confirm_password: "" },
  });

  const sendCode = requestForm.handleSubmit(async (values) => {
    setFormError(null);
    const normalized = normalizePhone(values.phone);
    if (!normalized) return;
    try {
      const result = unwrap(
        await api.POST("/api/v1/auth/password/reset/", { body: { phone: normalized } }),
      );
      setPhone(normalized);
      setRawPhone(values.phone);
      setNotice(result.detail);
    } catch (error) {
      setFormError(applyServerError(error, requestForm.setError, ["phone"]));
    }
  });

  const confirm = confirmForm.handleSubmit(async (values) => {
    if (!phone) return;
    setFormError(null);
    try {
      unwrap(
        await api.POST("/api/v1/auth/password/reset/confirm/", {
          body: { phone, code: values.code, new_password: values.new_password },
        }),
      );
      router.replace({
        pathname: "/login",
        params: {
          notice: "Password updated. Log in with your new password.",
          phone: rawPhone,
        },
      });
    } catch (error) {
      setFormError(
        applyServerError(error, confirmForm.setError, ["code", "new_password"]),
      );
    }
  });

  return (
    <Screen title="Reset password" back>
      {formError ? <Banner message={formError} /> : null}

      {phone === null ? (
        <>
          <Text className="mb-6 mt-2 text-base text-muted">
            Enter your phone number and we will text you a 6-digit code.
          </Text>
          <FormInput
            control={requestForm.control}
            name="phone"
            label="Phone number"
            placeholder="0712 345 678"
            keyboardType="phone-pad"
            autoComplete="tel"
          />
          <Button
            title="Send code"
            loading={requestForm.formState.isSubmitting}
            onPress={() => void sendCode()}
          />
        </>
      ) : (
        <>
          {notice ? <Banner tone="info" message={notice} /> : null}
          <Text className="mb-6 text-base text-muted">
            Enter the code sent to {phone} and choose a new password. You will be logged out
            on all devices.
          </Text>
          <FormInput
            control={confirmForm.control}
            name="code"
            label="SMS code"
            placeholder="123456"
            keyboardType="number-pad"
            autoComplete="one-time-code"
          />
          <FormInput
            control={confirmForm.control}
            name="new_password"
            label="New password"
            placeholder="At least 8 characters"
            secureTextEntry
            autoComplete="new-password"
          />
          <FormInput
            control={confirmForm.control}
            name="confirm_password"
            label="Confirm new password"
            secureTextEntry
            autoComplete="new-password"
          />
          <Button
            title="Set new password"
            loading={confirmForm.formState.isSubmitting}
            onPress={() => void confirm()}
          />
          <Button
            title="Use a different number"
            variant="ghost"
            className="mt-2"
            onPress={() => {
              setPhone(null);
              setNotice(null);
              setFormError(null);
            }}
          />
        </>
      )}
    </Screen>
  );
}
