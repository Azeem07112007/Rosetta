import { Link, useNavigate } from "react-router-dom";
import { Sun, Moon, LogOut, Menu, X } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../../features/auth/AuthContext";
import { useTheme } from "../../hooks/useTheme";
import { Button } from "../ui/Button";

export function Header() {
  const { user, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border-default bg-bg-primary/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-content items-center justify-between px-6">
        {/* Logo */}
        <Link
          to={user ? "/app" : "/"}
          className="flex items-center gap-2 text-lg font-semibold text-text-primary tracking-tight"
        >
          <span className="font-mono text-accent">{"{ }"}</span>
          Rosetta
        </Link>

        {/* Desktop navigation */}
        <nav className="hidden items-center gap-1 md:flex">
          {user ? (
            <>
              <Link to="/app">
                <Button variant="ghost" size="sm">Dashboard</Button>
              </Link>
              <Link to="/app/translate">
                <Button variant="ghost" size="sm">Translate</Button>
              </Link>
              <Link to="/app/history">
                <Button variant="ghost" size="sm">History</Button>
              </Link>
              <Link to="/app/settings">
                <Button variant="ghost" size="sm">Settings</Button>
              </Link>
              <div className="mx-2 h-5 w-px bg-border-default" />
              <button
                onClick={toggleTheme}
                className="flex h-8 w-8 items-center justify-center rounded-md text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors duration-120"
                aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              >
                {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
              </button>
              <Button variant="ghost" size="sm" onClick={handleSignOut}>
                <LogOut size={16} />
                Sign out
              </Button>
            </>
          ) : (
            <>
              <button
                onClick={toggleTheme}
                className="flex h-8 w-8 items-center justify-center rounded-md text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors duration-120"
                aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              >
                {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
              </button>
              <Link to="/signin">
                <Button variant="ghost" size="sm">Sign in</Button>
              </Link>
              <Link to="/signup">
                <Button variant="primary" size="sm">Get started</Button>
              </Link>
            </>
          )}
        </nav>

        {/* Mobile menu toggle */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="flex h-8 w-8 items-center justify-center rounded-md text-text-secondary hover:bg-bg-tertiary md:hidden"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Mobile navigation */}
      {mobileOpen && (
        <nav className="border-t border-border-subtle px-6 py-4 md:hidden">
          <div className="flex flex-col gap-2">
            {user ? (
              <>
                <Link to="/app" onClick={() => setMobileOpen(false)} className="text-sm text-text-primary py-2">Dashboard</Link>
                <Link to="/app/translate" onClick={() => setMobileOpen(false)} className="text-sm text-text-primary py-2">Translate</Link>
                <Link to="/app/history" onClick={() => setMobileOpen(false)} className="text-sm text-text-primary py-2">History</Link>
                <Link to="/app/settings" onClick={() => setMobileOpen(false)} className="text-sm text-text-primary py-2">Settings</Link>
                <button onClick={handleSignOut} className="text-sm text-text-secondary py-2 text-left">Sign out</button>
              </>
            ) : (
              <>
                <Link to="/signin" onClick={() => setMobileOpen(false)} className="text-sm text-text-primary py-2">Sign in</Link>
                <Link to="/signup" onClick={() => setMobileOpen(false)} className="text-sm text-accent py-2">Get started</Link>
              </>
            )}
            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 text-sm text-text-secondary py-2"
            >
              {theme === "light" ? <Moon size={14} /> : <Sun size={14} />}
              {theme === "light" ? "Dark mode" : "Light mode"}
            </button>
          </div>
        </nav>
      )}
    </header>
  );
}
