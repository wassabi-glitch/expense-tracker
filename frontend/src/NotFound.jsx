import { Link } from "react-router-dom";
import { Button } from "./components/ui/button";
import { isLoggedIn } from "./api";

export default function NotFound() {
  const authed = isLoggedIn();
  const target = authed ? "/dashboard" : "/sign-in";
  const label = authed ? "Back to dashboard" : "Go to sign in";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-4 text-center">
        <p className="text-sm font-medium text-muted-foreground">404</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">Page not found</h1>
        <p className="mt-3 text-muted-foreground">
          The page you requested does not exist or the URL is incorrect.
        </p>
        <Button asChild className="mt-6">
          <Link to={target}>{label}</Link>
        </Button>
      </div>
    </div>
  );
}
