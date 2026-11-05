import { ApiError, applyFieldErrors } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { AuthShell, FormBanner } from "@/pages/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { errorMessage, http } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { passwordSchema, phoneForApi, phoneSchema } from "@/lib/validation";

const requestSchema = z.object({ phone: phoneSchema });
type RequestValues = z.infer<typeof requestSchema>;

const confirmSchema = z
  .object({
    code: z.string().trim().regex(/^\d{6}$/, "Enter the 6-digit code."),
    new_password: passwordSchema,
    confirm: z.string(),
  })
  .refine((values) => values.new_password === values.confirm, {
    path: ["confirm"],
    message: "Passwords do not match.",
  });
type ConfirmValues = z.infer<typeof confirmSchema>;

function RequestStep({ onSent }: { onSent: (phone: string) => void }) {
  const [banner, setBanner] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RequestValues>({
    resolver: zodResolver(requestSchema),
    defaultValues: { phone: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setBanner(null);
    const phone = phoneForApi(values.phone);
    try {
      await http.post("/api/v1/auth/password/reset/", { body: { phone } });
      onSent(phone);
    } catch (error) {
      if (error instanceof ApiError) {
        applyFieldErrors(error, (name, err) =>
          setError(name as keyof RequestValues, err),
        );
      }
      setBanner(errorMessage(error));
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormBanner message={banner} />
      <Field label="Phone number" htmlFor="fp-phone" error={errors.phone?.message}>
        <Input
          id="fp-phone"
          type="tel"
          autoComplete="tel"
          placeholder="0712 345 678"
          {...register("phone")}
        />
      </Field>
      <Button type="submit" className="w-full" loading={isSubmitting}>
        Send reset code
      </Button>
    </form>
  );
}

function ConfirmStep({ phone, onBack }: { phone: string; onBack: () => void }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [banner, setBanner] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ConfirmValues>({
    resolver: zodResolver(confirmSchema),
    defaultValues: { code: "", new_password: "", confirm: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setBanner(null);
    try {
      await http.post("/api/v1/auth/password/reset/confirm/", {
        body: { phone, code: values.code, new_password: values.new_password },
      });
      toast.success("Password updated. Log in with your new password.");
      navigate("/login", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        applyFieldErrors(error, (name, err) =>
          setError(name as keyof ConfirmValues, err),
        );
      }
      setBanner(errorMessage(error));
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormBanner message={banner} />
      <p className="rounded-xl bg-surface-muted px-3 py-2 text-sm text-muted">
        If {phone} belongs to an account, a 6-digit code was sent by SMS.
      </p>
      <Field label="6-digit code" htmlFor="fp-code" error={errors.code?.message}>
        <Input
          id="fp-code"
          inputMode="numeric"
          maxLength={6}
          autoComplete="one-time-code"
          {...register("code")}
        />
      </Field>
      <Field label="New password" htmlFor="fp-new" error={errors.new_password?.message}>
        <Input
          id="fp-new"
          type="password"
          autoComplete="new-password"
          {...register("new_password")}
        />
      </Field>
      <Field label="Confirm new password" htmlFor="fp-confirm" error={errors.confirm?.message}>
        <Input
          id="fp-confirm"
          type="password"
          autoComplete="new-password"
          {...register("confirm")}
        />
      </Field>
      <Button type="submit" className="w-full" loading={isSubmitting}>
        Set new password
      </Button>
      <Button type="button" variant="ghost" className="w-full" onClick={onBack}>
        Use a different number
      </Button>
    </form>
  );
}

export default function ForgotPasswordPage() {
  const [phone, setPhone] = useState<string | null>(null);

  return (
    <AuthShell
      title="Reset your password"
      subtitle={
        phone
          ? "Enter the code we sent and choose a new password."
          : "We will text you a 6-digit reset code."
      }
      footer={
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Back to log in
        </Link>
      }
    >
      {phone ? (
        <ConfirmStep phone={phone} onBack={() => setPhone(null)} />
      ) : (
        <RequestStep onSent={setPhone} />
      )}
    </AuthShell>
  );
}
