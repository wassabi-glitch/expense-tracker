import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./components/ui/dialog";
import { getCurrentUser, logout } from "./api";

const CURRENCY_KEY = "settings.currency";
const DATE_FORMAT_KEY = "settings.date_format";

function getStoredPreference(key, fallback) {
  const value = localStorage.getItem(key);
  return value || fallback;
}

export default function Settings() {
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");

  const savedCurrency = useMemo(
    () => getStoredPreference(CURRENCY_KEY, "UZS"),
    []
  );
  const savedDateFormat = useMemo(
    () => getStoredPreference(DATE_FORMAT_KEY, "YYYY-MM-DD"),
    []
  );

  const [logoutOpen, setLogoutOpen] = useState(false);

  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const user = await getCurrentUser();
        setUsername(user?.username || "");
        setEmail(user?.email || "");
      } catch (e) {
        setError(e.message || "Failed to load profile");
      }
    };
    loadCurrentUser();
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/sign-in", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
          <p className="text-muted-foreground">Manage your profile and preferences.</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Account profile editing is not wired on backend yet.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input value={username} placeholder="Username" readOnly disabled />
            <Input value={email} placeholder="Email" type="email" readOnly disabled />
            <div className="md:col-span-2 flex gap-3">
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90" disabled>
                Save
              </Button>
              <Button variant="outline" disabled>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Password</CardTitle>
            <CardDescription>Password change is not wired on backend yet.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Current password" type="password" disabled />
            <Input placeholder="New password" type="password" disabled />
            <div className="md:col-span-2">
              <Button variant="outline" disabled>
                Update password
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>Preferences editing is not wired yet.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input value={savedCurrency === "UZS" ? "UZS - so'm" : savedCurrency} readOnly disabled />
            <Input value={savedDateFormat} readOnly disabled />
            <div className="md:col-span-2">
              <Button variant="outline" disabled>
                Update preferences
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Session</CardTitle>
            <CardDescription>Sign out of your account.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="destructive" onClick={() => setLogoutOpen(true)}>
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>

      <Dialog open={logoutOpen} onOpenChange={setLogoutOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sign out?</DialogTitle>
            <DialogDescription>You will be signed out and redirected to the sign-in page.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLogoutOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleLogout}>
              Sign out
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
