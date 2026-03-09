import React from "react";
import { Card } from "@/components/ui/card";
import { useTranslation } from "react-i18next";
import flowIcon from "@/assets/brand/sarflog-flow-icon.svg";
import flowLockup from "@/assets/brand/sarflog-flow-lockup.svg";

export function AuthFormCard({ title, description, backButton, children }) {
    const { t } = useTranslation();

    return (
        <div className="w-full min-h-screen lg:grid lg:grid-cols-2">
            {/* LEFT SIDE */}
            <div className="hidden lg:flex flex-col justify-between bg-zinc-950 text-white p-12 relative overflow-hidden h-full">
                {/* --- 1. THE MODERN PATTERN LAYER --- */}
                <div
                    className="absolute inset-0 z-0 opacity-[0.15]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' viewBox='0 0 100 100' preserveAspectRatio='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='%23a1a1aa' stroke-width='0.5' d='M0 0 C 20 10, 40 30, 60 40 S 80 60, 100 100 M0 20 C 20 30, 40 50, 60 60 S 80 80, 100 120 M0 40 C 20 50, 40 70, 60 80 S 80 100, 100 140 M0 60 C 20 70, 40 90, 60 100 S 80 120, 100 160 M0 80 C 20 90, 40 110, 60 120 S 80 140, 100 180' vector-effect='non-scaling-stroke'/%3E%3C/svg%3E")`,
                        backgroundSize: "cover",
                    }}
                ></div>

                <div className="absolute inset-0 z-0 bg-gradient-to-br from-transparent via-zinc-200/5 to-zinc-400/10"></div>

                {/* --- 2. TOP CONTENT (Branding) --- */}
                <div className="relative z-10 flex items-center gap-3">
                    <img
                        src={flowIcon}
                        alt="Sarflog logo"
                        className="h-11 w-11 object-contain"
                    />
                    <span className="font-mono text-sm tracking-widest uppercase text-zinc-400">
                        Sarflog v1.0.0
                    </span>
                </div>

                {/* --- 3. BOTTOM CONTENT (Specs) --- */}
                <div className="relative z-10 space-y-6">
                    <h2 className="text-3xl font-bold leading-tight tracking-tighter">
                        Financial data infrastructure.
                    </h2>

                    <div className="grid grid-cols-2 gap-4 border-t border-zinc-800 pt-6">
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">{t("auth.status", { defaultValue: "Status" })}</p>
                            <div className="flex items-center gap-2">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                <p className="font-medium text-sm text-emerald-400">{t("auth.operational", { defaultValue: "Operational" })}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* RIGHT SIDE */}
            <div className="relative flex h-full min-h-screen w-full items-start lg:items-center justify-center bg-white px-4 pt-12 pb-8 sm:pt-16 sm:pb-10 lg:py-12">
                {backButton}
                <Card className="w-full max-w-md md:max-w-lg border-0 bg-transparent p-0 shadow-none">
                    <div className="px-6 py-6 sm:px-8 sm:py-8">
                        <div className="mb-6 h-5" />

                        <div className="mb-6 text-center">
                            <div className="mb-5 flex items-center justify-center ml-15">
                                <img src={flowLockup} alt="Sarflog logo" className="h-10 w-auto object-contain" />
                            </div>
                            <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
                            {description && <p className="mt-2 text-sm text-muted-foreground">{description}</p>}
                        </div>

                        {children}
                    </div>
                </Card>
            </div>
        </div>
    );
}
