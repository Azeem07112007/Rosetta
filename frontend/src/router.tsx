import { createBrowserRouter } from "react-router-dom";
import { lazy, Suspense } from "react";
import { PublicLayout, AppLayout, AuthLayout } from "./components/layout/Layouts";

// Route-level code splitting
const LandingPage = lazy(() => import("./features/auth/LandingPage"));
const SignInPage = lazy(() => import("./features/auth/SignInPage"));
const SignUpPage = lazy(() => import("./features/auth/SignUpPage"));
const ResetPasswordPage = lazy(() => import("./features/auth/ResetPasswordPage"));
const DashboardPage = lazy(() => import("./features/translate/DashboardPage"));
const TranslatePage = lazy(() => import("./features/translate/TranslatePage"));
const TranslationDetailPage = lazy(() => import("./features/translate/TranslationDetailPage"));
const HistoryPage = lazy(() => import("./features/history/HistoryPage"));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage"));
const PrivacyPage = lazy(() => import("./features/auth/PrivacyPage"));
const TermsPage = lazy(() => import("./features/auth/TermsPage"));
const NotFoundPage = lazy(() => import("./features/auth/NotFoundPage"));

function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
    </div>
  );
}

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      {
        path: "/",
        element: <SuspenseWrapper><LandingPage /></SuspenseWrapper>,
      },
      {
        path: "/privacy",
        element: <SuspenseWrapper><PrivacyPage /></SuspenseWrapper>,
      },
      {
        path: "/terms",
        element: <SuspenseWrapper><TermsPage /></SuspenseWrapper>,
      },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      {
        path: "/signin",
        element: <SuspenseWrapper><SignInPage /></SuspenseWrapper>,
      },
      {
        path: "/signup",
        element: <SuspenseWrapper><SignUpPage /></SuspenseWrapper>,
      },
      {
        path: "/reset-password",
        element: <SuspenseWrapper><ResetPasswordPage /></SuspenseWrapper>,
      },
    ],
  },
  {
    element: <AppLayout />,
    children: [
      {
        path: "/app",
        element: <SuspenseWrapper><DashboardPage /></SuspenseWrapper>,
      },
      {
        path: "/app/translate",
        element: <SuspenseWrapper><TranslatePage /></SuspenseWrapper>,
      },
      {
        path: "/app/translate/:id",
        element: <SuspenseWrapper><TranslationDetailPage /></SuspenseWrapper>,
      },
      {
        path: "/app/history",
        element: <SuspenseWrapper><HistoryPage /></SuspenseWrapper>,
      },
      {
        path: "/app/settings",
        element: <SuspenseWrapper><SettingsPage /></SuspenseWrapper>,
      },
    ],
  },
  {
    path: "*",
    element: <SuspenseWrapper><NotFoundPage /></SuspenseWrapper>,
  },
]);
