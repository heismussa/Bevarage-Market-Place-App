import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { View } from "react-native";

import { Button } from "@/components/Button";
import { FormInput } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { Banner } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { applyServerError } from "@/lib/forms";
import { useToast } from "@/lib/toast";
import { changePasswordSchema, type ChangePasswordForm } from "@/lib/validation";

export default function ChangePasswordScreen() {
  const router = useRouter();
  const toast = useToast();
  const { replaceTokens } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const { control, handleSubmit, setError, formState } = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const tokens = unwrap(
        await api.POST("/api/v1/auth/password/change/", {
          body: {
            current_password: values.current_password,
            new_password: values.new_password,
          },
        }),
      );
      await replaceTokens({ access: tokens.access, refresh: tokens.refresh });
      toast.show("Password updated. Other devices were logged out.", "success");
      router.back();
    } catch (error) {
      setFormError(
        applyServerError(error, setError, ["current_password", "new_password"]),
      );
    }
  });

  return (
    <Screen title="Change password" back>
      <View>
        {formError ? <Banner message={formError} /> : null}
        <FormInput
          control={control}
          name="current_password"
          label="Current password"
          secureTextEntry
          autoComplete="password"
        />
        <FormInput
          control={control}
          name="new_password"
          label="New password"
          secureTextEntry
          autoComplete="new-password"
        />
        <FormInput
          control={control}
          name="confirm_password"
          label="Confirm new password"
          secureTextEntry
          autoComplete="new-password"
        />
        <Button
          title="Update password"
          loading={formState.isSubmitting}
          onPress={() => void onSubmit()}
        />
      </View>
    </Screen>
  );
}
