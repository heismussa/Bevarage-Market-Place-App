import { ApiError, applyFieldErrors } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/lib/toast";

const schema = z
  .object({
    current_password: z.string().min(1, "Enter your current password."),
    new_password: z.string().min(8, "Use at least 8 characters."),
    confirm: z.string(),
  })
  .refine((values) => values.new_password === values.confirm, {
    path: ["confirm"],
    message: "Passwords do not match.",
  });

type Values = z.infer<typeof schema>;

export function ChangePasswordDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { changePassword } = useAuth();
  const toast = useToast();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: "", new_password: "", confirm: "" },
  });

  const close = () => {
    reset();
    onClose();
  };

  const onSubmit = handleSubmit(async (values) => {
    try {
      await changePassword(values.current_password, values.new_password);
      toast.success("Password changed. Other devices were logged out.");
      close();
    } catch (error) {
      if (error instanceof ApiError) {
        applyFieldErrors(error, (name, err) =>
          setError(name as keyof Values, err),
        );
      }
      toast.error(errorMessage(error));
    }
  });

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Change password"
      description="Other devices will be logged out."
      className="max-w-md"
      footer={
        <>
          <Button variant="outline" onClick={close} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={onSubmit} loading={isSubmitting}>
            Change password
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          label="Current password"
          htmlFor="cp-current"
          error={errors.current_password?.message}
        >
          <Input
            id="cp-current"
            type="password"
            autoComplete="current-password"
            {...register("current_password")}
          />
        </Field>
        <Field
          label="New password"
          htmlFor="cp-new"
          error={errors.new_password?.message}
        >
          <Input
            id="cp-new"
            type="password"
            autoComplete="new-password"
            {...register("new_password")}
          />
        </Field>
        <Field
          label="Confirm new password"
          htmlFor="cp-confirm"
          error={errors.confirm?.message}
        >
          <Input
            id="cp-confirm"
            type="password"
            autoComplete="new-password"
            {...register("confirm")}
          />
        </Field>
        <button type="submit" className="hidden" />
      </form>
    </Dialog>
  );
}
