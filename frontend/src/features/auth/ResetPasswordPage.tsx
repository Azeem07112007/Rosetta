import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "./AuthContext";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

const resetSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});

type ResetForm = z.infer<typeof resetSchema>;

export default function ResetPasswordPage() {
  const { resetPassword } = useAuth();
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
  });

  const onSubmit = async (data: ResetForm) => {
    setLoading(true);
    try {
      await resetPassword(data.email);
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setLoading(false);
      setSent(true);
    }
  };

  if (sent) {
    return (
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Check your email</h1>
        <p className="mt-2 text-sm text-text-secondary">
          If an account with that email exists, we sent a password reset link. Check your inbox and spam folder.
        </p>
        <Link to="/signin">
          <Button variant="secondary" className="mt-6">
            Back to sign in
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-text-primary">Reset your password</h1>
      <p className="mt-2 text-sm text-text-secondary">
        Enter the email associated with your account and we will send a reset link.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          error={errors.email?.message}
          {...register("email")}
        />

        <Button type="submit" loading={loading} className="w-full">
          Send reset link
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-secondary">
        Remember your password?{" "}
        <Link to="/signin" className="text-accent hover:text-accent-hover transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  );
}
