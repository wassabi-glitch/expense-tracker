import { useState } from "react";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardFooter,
    CardDescription
} from "./components/ui/card";
import authBg from "./assets/auth-bg1.jpg";
import { signup } from "./api";

export default function Signup() {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [status, setStatus] = useState("");

    async function handleSubmit(e) {
        e.preventDefault();
        setStatus("Creating account...");
        try {
            await signup(username, email, password);
            setStatus("Signup success");
        } catch (err) {
            setStatus(err.message || "Signup failed");
        }
    }

    return (
        <div className="w-full min-h-screen lg:grid lg:grid-cols-2">

            {/* LEFT SIDE */}
            <div className="hidden lg:flex flex-col justify-between bg-zinc-950 text-white p-12 relative overflow-hidden h-full">

                {/* --- 1. THE MODERN PATTERN LAYER --- */}
                {/* This replaces the <img> tag. It's a subtle SVG pattern. */}
                <div
                    className="absolute inset-0 z-0 opacity-[0.15]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' viewBox='0 0 100 100' preserveAspectRatio='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='%23a1a1aa' stroke-width='0.5' d='M0 0 C 20 10, 40 30, 60 40 S 80 60, 100 100 M0 20 C 20 30, 40 50, 60 60 S 80 80, 100 120 M0 40 C 20 50, 40 70, 60 80 S 80 100, 100 140 M0 60 C 20 70, 40 90, 60 100 S 80 120, 100 160 M0 80 C 20 90, 40 110, 60 120 S 80 140, 100 180' vector-effect='non-scaling-stroke'/%3E%3C/svg%3E")`,
                        backgroundSize: "cover",
                        // Optional: Add a subtle pulse animation
                        // animation: "pulse 10s cubic-bezier(0.4, 0, 0.6, 1) infinite"
                    }}
                ></div>

                {/* --- Optional: A subtle noise texture overlay for grit --- */}
                <div className="absolute inset-0 z-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] mix-blend-overlay"></div>


                {/* --- 2. TOP CONTENT (Branding) --- */}
                <div className="relative z-10 flex items-center gap-3">
                    <div className="h-8 w-8 bg-white rounded-sm flex items-center justify-center">
                        <span className="text-zinc-950 font-bold font-mono">/</span>
                    </div>
                    <span className="font-mono text-sm tracking-widest uppercase text-zinc-400">
                        ExpenseTracker_v1.0
                    </span>
                </div>

                {/* --- 3. BOTTOM CONTENT (Specs) --- */}
                <div className="relative z-10 space-y-6">
                    <h2 className="text-3xl font-bold leading-tight tracking-tighter">
                        Financial data infrastructure.
                    </h2>

                    <div className="grid grid-cols-2 gap-4 border-t border-zinc-800 pt-6">
                        {/* <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Stack</p>
                            <p className="font-medium text-sm">React + FastAPI</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Storage</p>
                            <p className="font-medium text-sm">Postgres Docker</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Auth</p>
                            <p className="font-medium text-sm">JWT Secure</p>
                        </div> */}
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Status</p>
                            <div className="flex items-center gap-2">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                <p className="font-medium text-sm text-emerald-400">Operational</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* RIGHT SIDE (Form) */}
            <div className="flex h-full min-h-screen w-full items-center justify-center bg-slate-50 px-4 py-12"
                style={{
                    backgroundImage: "radial-gradient(#cbd5e1 1px, transparent 1px)",
                    backgroundSize: "32px 32px"
                }}>

                <Card className="w-full max-w-md md:max-w-lg shadow-xl border-0 sm:border bg-white">
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl font-bold text-center">Create an account</CardTitle>
                        <CardDescription className="text-center">
                            Enter your details below to get started
                        </CardDescription>
                    </CardHeader>

                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="flex flex-col gap-2">
                                <Label htmlFor="username">Username</Label>
                                <Input
                                    id="username"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="johndoe"
                                    required
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@example.com"
                                    required
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <Label htmlFor="password">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="********"
                                    required
                                />
                            </div>

                            <Button className="w-full bg-zinc-900 hover:bg-zinc-800 text-white" type="submit">
                                Create account
                            </Button>

                            {status && (
                                <p className={`text-sm text-center mt-2 ${status.toLowerCase().includes('success') ? 'text-green-600' : 'text-red-500'}`}>
                                    {status}
                                </p>
                            )}
                        </form>
                    </CardContent>

                    <CardFooter className="justify-center">
                        <div className="text-center text-sm text-muted-foreground">
                            Already have an account?{" "}
                            <a href="/sign-in" className="underline font-medium text-zinc-900 hover:text-zinc-700">
                                Sign in
                            </a>
                        </div>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
