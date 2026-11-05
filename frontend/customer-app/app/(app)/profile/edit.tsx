import { formatPhoneDisplay } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { View } from "react-native";

import { Button } from "@/components/Button";
import { FormInput } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { Banner, ErrorView, LoadingView } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { applyServerError } from "@/lib/forms";
import { keys } from "@/lib/query";
import { useToast } from "@/lib/toast";
import { phoneForApi, profileSchema, type ProfileForm } from "@/lib/validation";

export default function EditProfileScreen() {
  const router = useRouter();
  const toast = useToast();
  const { setUser } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const me = useQuery({
    queryKey: keys.me,
    queryFn: async () => unwrap(await api.GET("/api/v1/auth/me/")),
  });

  const { control, handleSubmit, setError, formState, reset } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    values: me.data
      ? {
          full_name: me.data.full_name,
          phone: formatPhoneDisplay(me.data.phone),
          email: me.data.email ?? "",
        }
      : undefined,
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const user = unwrap(
        await api.PATCH("/api/v1/auth/me/", {
          body: {
            full_name: values.full_name.trim(),
            phone: phoneForApi(values.phone),
            email: values.email.trim() || null,
          },
        }),
      );
      setUser(user);
      reset({
        full_name: user.full_name,
        phone: formatPhoneDisplay(user.phone),
        email: user.email ?? "",
      });
      toast.show("Profile updated.", "success");
      router.back();
    } catch (error) {
      setFormError(
        applyServerError(error, setError, ["full_name", "phone", "email"]),
      );
    }
  });

  return (
    <Screen title="Edit profile" back>
      {me.isLoading ? <LoadingView /> : null}
      {me.isError ? <ErrorView error={me.error} onRetry={() => void me.refetch()} /> : null}
      {me.data ? (
        <View>
          {formError ? <Banner message={formError} /> : null}
          <FormInput
            control={control}
            name="full_name"
            label="Full name"
            autoCapitalize="words"
            autoComplete="name"
          />
          <FormInput
            control={control}
            name="phone"
            label="Phone number"
            keyboardType="phone-pad"
            autoComplete="tel"
          />
          <FormInput
            control={control}
            name="email"
            label="Email (optional)"
            keyboardType="email-address"
            autoComplete="email"
          />
          <Button
            title="Save"
            loading={formState.isSubmitting}
            onPress={() => void onSubmit()}
          />
        </View>
      ) : null}
    </Screen>
  );
}
