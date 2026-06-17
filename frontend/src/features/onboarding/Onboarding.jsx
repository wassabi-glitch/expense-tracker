import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AuthFormCard } from "@/components/AuthFormCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { getCurrentUser } from "@/lib/api";
import { formatAmountInput, formatUzs, parseAmountInput } from "@/lib/format";
import {
    onboardingSchema,
    onboardingStepOneSchema,
    onboardingStepTwoSchema,
    MAX_INCOME_AMOUNT_DIGITS,
} from "./onboardingSchemas";
import { useOnboardingUpsertMutation } from "./hooks/useOnboardingMutations";

const LIFE_STATUS_CONFIG = [
    { value: "student", labelKey: "onboarding.lifeStatus.student", fallback: "Student" },
    { value: "employed", labelKey: "onboarding.lifeStatus.employed", fallback: "Employed" },
    { value: "self_employed", labelKey: "onboarding.lifeStatus.selfEmployed", fallback: "Self-employed" },
    { value: "business_owner", labelKey: "onboarding.lifeStatus.businessOwner", fallback: "Business owner" },
    { value: "unemployed", labelKey: "onboarding.lifeStatus.unemployed", fallback: "Unemployed" },
];

const STEP_QUESTION_CLASS = "text-sm font-medium text-foreground";
const ONBOARDING_INPUT_CLASS = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
const DISABLED_BUTTON_CURSOR_CLASS = "disabled:pointer-events-auto disabled:cursor-not-allowed";
const TOTAL_STEPS = 2;

export default function Onboarding() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [lifeStatuses, setLifeStatuses] = useState([]);
    const [wallets, setWallets] = useState([{ name: "Cash", initial_balance: "0", color: "default" }]);
    const [status, setStatus] = useState("");
    const [fieldErrors, setFieldErrors] = useState({});

    // Temporary inputs for 'Add Wallet' UI
    const [newWalletName, setNewWalletName] = useState("");
    const [newWalletBalance, setNewWalletBalance] = useState("");

    const userQuery = useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });
    const onboardingMutation = useOnboardingUpsertMutation();
    const isSubmitting = onboardingMutation.isPending;
    const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);

    const stepOneParsed = useMemo(
        () => onboardingStepOneSchema.safeParse({ life_statuses: lifeStatuses }),
        [lifeStatuses]
    );
    const stepTwoParsed = useMemo(
        () => onboardingStepTwoSchema.safeParse({ wallets }),
        [wallets]
    );
    const fullParsed = useMemo(
        () =>
            onboardingSchema.safeParse({
                life_statuses: lifeStatuses,
                wallets,
            }),
        [lifeStatuses, wallets]
    );

    const stepOneIssue = useMemo(() => {
        if (stepOneParsed.success) return "";
        const issue = stepOneParsed.error.issues.find((item) => item.path?.[0] === "life_statuses");
        return issue ? translateValidation(issue.message) : "";
    }, [stepOneParsed, translateValidation]);

    const stepTwoIssue = useMemo(() => {
        if (stepTwoParsed.success) return "";
        const issue = stepTwoParsed.error.issues.find((item) => item.path?.[0] === "wallets");
        return issue ? translateValidation(issue.message) : "";
    }, [stepTwoParsed, translateValidation]);

    const canContinueStepOne = stepOneParsed.success;
    const canSubmit = fullParsed.success && !isSubmitting;
    const progressValue = (step / TOTAL_STEPS) * 100;

    if (userQuery.isPending) return null;

    if (userQuery.isError) {
        return (
            <AuthFormCard
                title={t("onboarding.title", { defaultValue: "Complete your onboarding" })}
                description={t("onboarding.retryHint", { defaultValue: "We could not load your account profile. Please retry." })}
            >
                <Button className="h-11 w-full" onClick={() => userQuery.refetch()}>
                    {t("onboarding.retryAction", { defaultValue: "Retry" })}
                </Button>
            </AuthFormCard>
        );
    }

    function handleStepOneContinue(e) {
        e.preventDefault();
        setStatus("");
        setFieldErrors({});

        if (!stepOneParsed.success) {
            setFieldErrors({
                life_statuses: stepOneIssue || t("onboarding.validation.lifeStatus.required", {
                    defaultValue: "Please select your current situation.",
                }),
            });
            return;
        }
        setStep(2);
    }

    function handleAddWallet() {
        if (!newWalletName.trim()) return;
        setWallets([...wallets, { 
            name: newWalletName, 
            initial_balance: newWalletBalance || "0", 
            color: "default" 
        }]);
        setNewWalletName("");
        setNewWalletBalance("");
    }

    function removeWallet(index) {
        setWallets(wallets.filter((_, i) => i !== index));
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setStatus("");
        setFieldErrors({});

        const parsed = onboardingSchema.safeParse({
            life_statuses: lifeStatuses,
            wallets,
        });

        if (!parsed.success) {
            const newErrors = {};
            parsed.error.issues.forEach((issue) => {
                const path = issue.path[0];
                if (path) {
                    newErrors[path] = t(issue.message, { defaultValue: issue.message });
                }
            });
            setFieldErrors(newErrors);
            setStatus(t("onboarding.validation.fixErrors", { defaultValue: "Please fix the errors above before continuing." }));
            return;
        }

        try {
            await onboardingMutation.mutateAsync({
                life_statuses: parsed.data.life_statuses,
                wallets: parsed.data.wallets,
            });
            navigate("/dashboard", { replace: true });
        } catch (err) {
            const msg = String(err?.message || "");
            if (msg === "income.amount_too_large" || msg === "profile.initial_balance_too_large") {
                setFieldErrors({
                    initial_balance: t("onboarding.validation.initialBalance.max", {
                        defaultValue: "Amount cannot exceed 999,999,999,999.",
                    }),
                });
                return;
            }
            setStatus(t(msg, { defaultValue: msg || t("onboarding.submitFailed", { defaultValue: "Failed to save onboarding data." }) }));
        }
    }

    return (
        <AuthFormCard
            title={t("onboarding.title", { defaultValue: "Complete your onboarding" })}
            description={t("onboarding.description", { defaultValue: "Two quick steps to personalize your experience." })}
            backButton={
                step > 1 ? (
                    <button
                        type="button"
                        onClick={() => {
                            setStep((currentStep) => Math.max(1, currentStep - 1));
                            setStatus("");
                            setFieldErrors({});
                        }}
                        className="absolute left-4 top-4 sm:left-8 sm:top-8 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span>{t("common.back")}</span>
                    </button>
                ) : null
            }
        >
            <div className="mb-5 space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                        {t("onboarding.progressLabel", {
                            defaultValue: "Step {{current}} of {{total}}",
                            current: step,
                            total: TOTAL_STEPS,
                        })}
                    </span>
                    <span>{Math.round(progressValue)}%</span>
                </div>
                <Progress value={progressValue} className="h-2" />
            </div>
            {step === 1 ? (
                <form onSubmit={handleStepOneContinue} className="space-y-3">
                    <p className={STEP_QUESTION_CLASS}>
                        {t("onboarding.step1.question", { defaultValue: "What best describes your situation?" })}
                    </p>

                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {LIFE_STATUS_CONFIG.map((option) => {
                            const selected = lifeStatuses.includes(option.value);
                            return (
                                <Button
                                    key={option.value}
                                    type="button"
                                    variant={selected ? "default" : "outline"}
                                    className="h-11 justify-start"
                                    onClick={() => {
                                        if (selected) {
                                            setLifeStatuses(lifeStatuses.filter(s => s !== option.value));
                                        } else {
                                            setLifeStatuses([...lifeStatuses, option.value]);
                                        }
                                        setStatus("");
                                        setFieldErrors((prev) => ({ ...prev, life_statuses: "" }));
                                    }}
                                >
                                    {t(option.labelKey, { defaultValue: option.fallback })}
                                </Button>
                            );
                        })}
                    </div>

                    <div className="min-h-2.5">
                        {!!(fieldErrors.life_statuses || stepOneIssue) && (
                            <p className="text-xs text-red-500">
                                {fieldErrors.life_statuses || stepOneIssue}
                            </p>
                        )}
                    </div>

                    <Button
                        className={`h-11 w-full ${DISABLED_BUTTON_CURSOR_CLASS}`}
                        type="submit"
                        disabled={!canContinueStepOne}
                    >
                        {t("auth.continue")}
                    </Button>

                    <div className="min-h-2.5">
                        {!!status && <p className="text-xs text-center text-red-500">{status}</p>}
                    </div>
                </form>
            ) : (
                <div className="space-y-4">
                    <div className="space-y-1">
                        <p className={STEP_QUESTION_CLASS}>
                            {t("onboarding.step2.question_wallets", {
                                defaultValue: "Setup your physical wallets",
                            })}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {t("onboarding.step2.description_wallets", {
                                defaultValue: "Add cash, cards or bank accounts you want to track separately.",
                            })}
                        </p>
                    </div>

                    <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1">
                        {wallets.map((w, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 rounded-lg border bg-accent/30">
                                <div>
                                    <p className="text-sm font-semibold">{w.name}</p>
                                    <p className="text-xs text-muted-foreground">{formatUzs(parseAmountInput(w.initial_balance))} UZS</p>
                                </div>
                                <Button variant="ghost" size="sm" onClick={() => removeWallet(idx)} disabled={wallets.length === 1}>
                                    {t("common.remove")}
                                </Button>
                            </div>
                        ))}
                    </div>

                    <div className="p-4 rounded-xl border-2 border-dashed border-emerald-500/30 bg-emerald-500/5 space-y-3">
                        <div className="grid grid-cols-2 gap-2">
                             <Input 
                                placeholder="Wallet Name (e.g. Card)" 
                                value={newWalletName}
                                onChange={e => setNewWalletName(e.target.value)}
                             />
                             <Input 
                                placeholder="Balance" 
                                type="text"
                                inputMode="numeric"
                                value={newWalletBalance}
                                onChange={e => setNewWalletBalance(formatAmountInput(e.target.value, 15))}
                             />
                        </div>
                        <Button type="button" variant="outline" className="w-full h-9 text-xs" onClick={handleAddWallet}>
                            {t("onboarding.action.addWallet", { defaultValue: "+ Add another wallet" })}
                        </Button>
                    </div>

                    <Button
                        className={`h-11 w-full mt-4 ${DISABLED_BUTTON_CURSOR_CLASS}`}
                        onClick={handleSubmit}
                        disabled={!canSubmit || isSubmitting}
                    >
                        {isSubmitting ? (
                            <span
                                aria-label="Loading"
                                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                            />
                        ) : (
                            t("onboarding.submitAction", { defaultValue: "Finish setup" })
                        )}
                    </Button>

                    <div className="min-h-2.5">
                        {!!status && <p className="text-xs text-center text-red-500">{status}</p>}
                    </div>
                </div>
            )}
        </AuthFormCard>
    );
}
