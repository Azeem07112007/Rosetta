import { Link } from "react-router-dom";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border-default bg-bg-primary">
      <div className="mx-auto flex max-w-content flex-col items-center justify-between gap-4 px-6 py-8 sm:flex-row">
        <p className="text-xs text-text-tertiary">
          {currentYear} Rosetta. All rights reserved.
        </p>
        <nav className="flex gap-6">
          <Link
            to="/privacy"
            className="text-xs text-text-tertiary hover:text-text-secondary transition-colors duration-120"
          >
            Privacy Policy
          </Link>
          <Link
            to="/terms"
            className="text-xs text-text-tertiary hover:text-text-secondary transition-colors duration-120"
          >
            Terms of Service
          </Link>
        </nav>
      </div>
    </footer>
  );
}
