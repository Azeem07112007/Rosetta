import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <p className="font-mono text-6xl font-bold text-text-tertiary">404</p>
      <h1 className="mt-4 text-xl font-semibold text-text-primary">Page not found</h1>
      <p className="mt-2 text-sm text-text-secondary">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link to="/" className="mt-6">
        <Button variant="secondary">Go to home page</Button>
      </Link>
    </div>
  );
}
