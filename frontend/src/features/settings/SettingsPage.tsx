import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { User, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { useAuth } from "../auth/AuthContext";
import { api, ApiClientError } from "../../lib/api";
import type { Account } from "../../types";
import { useEffect } from "react";

const displayNameSchema = z.object({
  display_name: z.string().min(1, "Display name is required").max(100),
});

type DisplayNameForm = z.infer<typeof displayNameSchema>;

export default function SettingsPage() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DisplayNameForm>({
    resolver: zodResolver(displayNameSchema),
  });

  useEffect(() => {
    async function load() {
      try {
        const data = await api.get<Account>("/account");
        setAccount(data);
        reset({ display_name: data.display_name || "" });
      } catch {
        // Account data unavailable
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [reset]);

  const onSubmit = async (data: DisplayNameForm) => {
    setSaving(true);
    setSaveMessage("");
    try {
      const updated = await api.patch<Account>("/account", data);
      setAccount(updated);
      setSaveMessage("Display name updated.");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setSaveMessage(err.message);
      } else {
        setSaveMessage("Failed to update.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await api.delete("/account");
      await signOut();
      navigate("/");
    } catch {
      setDeleting(false);
      setDeleteConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-semibold text-text-primary">Settings</h1>
      <p className="mt-1 text-sm text-text-secondary">Manage your account.</p>

      {/* Account info */}
      <section className="mt-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-accent-subtle">
            <User size={18} className="text-accent" />
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">{account?.email}</p>
            <p className="text-xs text-text-tertiary">
              Member since {account?.created_at ? new Date(account.created_at).toLocaleDateString() : "unknown"}
            </p>
          </div>
        </div>
      </section>

      {/* Display name form */}
      <section className="rounded-md border border-border-default bg-bg-secondary p-6">
        <h2 className="text-sm font-medium text-text-primary mb-4">Display name</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            placeholder="Your name"
            error={errors.display_name?.message}
            {...register("display_name")}
          />
          {saveMessage && (
            <p className="text-xs text-text-secondary">{saveMessage}</p>
          )}
          <Button type="submit" size="sm" loading={saving}>
            Save
          </Button>
        </form>
      </section>

      {/* Danger zone */}
      <section className="mt-8 rounded-md border border-error/30 p-6">
        <h2 className="text-sm font-medium text-error mb-2">Delete account</h2>
        <p className="text-xs text-text-secondary mb-4">
          Permanently delete your account and all translation history. This action cannot be undone.
        </p>

        {deleteConfirm ? (
          <div className="flex items-center gap-2">
            <Button
              variant="danger"
              size="sm"
              loading={deleting}
              onClick={handleDeleteAccount}
            >
              <Trash2 size={14} />
              Confirm deletion
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDeleteConfirm(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setDeleteConfirm(true)}
          >
            Delete account
          </Button>
        )}
      </section>
    </div>
  );
}
