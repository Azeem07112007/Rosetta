import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "./AuthContext";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

const signUpSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password must be 128 characters or fewer"),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type SignUpForm = z.infer<typeof signUpSchema>;

export default function SignUpPage() {
  const { signUp } = useAuth();
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignUpForm>({
    resolver: zodResolver(signUpSchema),
  });

  const onSubmit = async (data: SignUpForm) => {
    setServerError("");
    setLoading(true);
    try {
      await signUp(data.email, data.password);
      setSuccess(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Sign up failed. Please try again.";
      setServerError(message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Check your email</h1>
        <p className="mt-2 text-sm text-text-secondary">
          We sent a confirmation link to your email address. Click the link to activate your account.
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
      <h1 className="text-2xl font-semibold text-text-primary">Create your account</h1>
      <p className="mt-2 text-sm text-text-secondary">
        Start translating code between programming languages with Rosetta.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4" noValidate>
        {serverError && (
          <div className="rounded-md border border-error bg-error/5 px-4 py-3 text-sm text-error" role="alert">
            {serverError}
          </div>
        )}

        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          error={errors.email?.message}
          {...register("email")}
        />

        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 8 characters"
          error={errors.password?.message}
          {...register("password")}
        />

        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          placeholder="Repeat your password"
          error={errors.confirmPassword?.message}
          {...register("confirmPassword")}
        />

        <p className="text-xs text-text-tertiary">
          By creating an account, you agree to our{" "}
          <Link to="/terms" className="text-accent hover:text-accent-hover">Terms of Service</Link>
          {" "}and{" "}
          <Link to="/privacy" className="text-accent hover:text-accent-hover">Privacy Policy</Link>.
        </p>

        <Button type="submit" loading={loading} className="w-full">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-secondary">
        Already have an account?{" "}
        <Link to="/signin" className="text-accent hover:text-accent-hover transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  );
}
