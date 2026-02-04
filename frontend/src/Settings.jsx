import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";

export default function Settings() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
          <p className="text-muted-foreground">Manage your profile and preferences.</p>
        </div>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Update your account details.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Username" />
            <Input placeholder="Email" type="email" />
            <div className="md:col-span-2 flex gap-3">
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90">Save</Button>
              <Button variant="outline">Cancel</Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Password</CardTitle>
            <CardDescription>Change your password.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input placeholder="Current password" type="password" />
            <Input placeholder="New password" type="password" />
            <div className="md:col-span-2">
              <Button variant="outline">Update password</Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>Customize your defaults.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option>USD - $</option>
              <option>EUR - €</option>
              <option>GBP - £</option>
            </select>
            <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option>MM/DD/YYYY</option>
              <option>DD/MM/YYYY</option>
              <option>YYYY-MM-DD</option>
            </select>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Session</CardTitle>
            <CardDescription>Sign out of your account.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="destructive">Log out</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
