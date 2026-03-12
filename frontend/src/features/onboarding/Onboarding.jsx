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
import { formatAmountInput } from "@/lib/format";
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
    const [lifeStatus, setLifeStatus] = useState("");
    const [initialBalanceInput, setInitialBalanceInput] = useState("");
    const [status, setStatus] = useState("");
    const [fieldErrors, setFieldErrors] = useState({});

    const userQuery = useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });
    const onboardingMutation = useOnboardingUpsertMutation();
    const isSubmitting = onboardingMutation.isPending;
    const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);

    const stepOneParsed = useMemo(
        () => onboardingStepOneSchema.safeParse({ life_status: lifeStatus }),
        [lifeStatus]
    );
    const stepTwoParsed = useMemo(
        () => onboardingStepTwoSchema.safeParse({ initial_balance: initialBalanceInput }),
        [initialBalanceInput]
    );
    const fullParsed = useMemo(
        () =>
            onboardingSchema.safeParse({
                life_status: lifeStatus,
                initial_balance: initialBalanceInput,
            }),
        [lifeStatus, initialBalanceInput]
    );

    const stepOneIssue = useMemo(() => {
        if (stepOneParsed.success) return "";
        const issue = stepOneParsed.error.issues.find((item) => item.path?.[0] === "life_status");
        return issue ? translateValidation(issue.message) : "";
    }, [stepOneParsed, translateValidation]);

    const stepTwoIssue = useMemo(() => {
        if (stepTwoParsed.success) return "";
        const issue = stepTwoParsed.error.issues.find((item) => item.path?.[0] === "initial_balance");
        return issue ? translateValidation(issue.message) : "";
    }, [stepTwoParsed, translateValidation]);

    const canContinueStepOne = stepOneParsed.success;
    const canSubmit = fullParsed.success && !isSubmitting;
    const selectedLifeStatusLabel = LIFE_STATUS_CONFIG.find((item) => item.value === lifeStatus);
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
                life_status: stepOneIssue || t("onboarding.validation.lifeStatus.required", {
                    defaultValue: "Please select your current situation.",
                }),
            });
            return;
        }
        setStep(2);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setStatus("");
        setFieldErrors({});

        const parsed = onboardingSchema.safeParse({
            life_status: lifeStatus,
            initial_balance: initialBalanceInput,
        });

        if (!parsed.success) {
            const nextErrors = {};
            parsed.error.issues.forEach((issue) => {
                const field = issue.path?.[0];
                if (field && !nextErrors[field]) {
                    nextErrors[field] = translateValidation(issue.message);
                }
            });
            setFieldErrors(nextErrors);
            return;
        }

        try {
            await onboardingMutation.mutateAsync({
                life_status: parsed.data.life_status,
                initial_balance: parsed.data.initial_balance,
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
                            const selected = lifeStatus === option.value;
                            return (
                                <Button
                                    key={option.value}
                                    type="button"
                                    variant={selected ? "default" : "outline"}
                                    className="h-11 justify-start"
                                    onClick={() => {
                                        setLifeStatus(option.value);
                                        setStatus("");
                                        setFieldErrors((prev) => ({ ...prev, life_status: "" }));
                                    }}
                                >
                                    {t(option.labelKey, { defaultValue: option.fallback })}
                                </Button>
                            );
                        })}
                    </div>

                    <div className="min-h-2.5">
                        {!!(fieldErrors.life_status || stepOneIssue) && (
                            <p className="text-xs text-red-500">
                                {fieldErrors.life_status || stepOneIssue}
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
                <form onSubmit={handleSubmit} className="space-y-3">
                    <p className={STEP_QUESTION_CLASS}>
                        {t("onboarding.step2.question", {
                            defaultValue: "What is your current balance in UZS?",
                        })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                        {t("onboarding.step2.description", {
                            defaultValue: "This helps us show a more accurate starting view and better recommendations from day one.",
                        })}
                    </p>

                    {selectedLifeStatusLabel && (
                        <p className="text-xs text-muted-foreground">
                            {t("onboarding.selectedStatus", {
                                defaultValue: "Selected: {{status}}",
                                status: t(selectedLifeStatusLabel.labelKey, { defaultValue: selectedLifeStatusLabel.fallback }),
                            })}
                        </p>
                    )}

                    <div className="space-y-0.5">
                        <Input
                            id="initial-balance"
                            type="text"
                            inputMode="numeric"
                            maxLength={15}
                            value={initialBalanceInput}
                            onChange={(e) => {
                                setInitialBalanceInput(formatAmountInput(e.target.value, MAX_INCOME_AMOUNT_DIGITS));
                                setStatus("");
                                setFieldErrors((prev) => ({ ...prev, initial_balance: "" }));
                            }}
                            onKeyDown={(e) => {
                                if (
                                    e.key === "-" ||
                                    e.key === "+" ||
                                    e.key === "." ||
                                    e.key.toLowerCase() === "e"
                                ) {
                                    e.preventDefault();
                                }
                            }}
                            className={`${ONBOARDING_INPUT_CLASS} ${fieldErrors.initial_balance || (initialBalanceInput.trim().length > 0 && stepTwoIssue) ? "border-red-500 focus-visible:border-red-500" : ""}`}
                            placeholder={t("onboarding.placeholder.initialBalance", {
                                defaultValue: "Initial balance",
                            })}
                            required
                        />
                        <div className="min-h-2.5">
                            {!!(fieldErrors.initial_balance || (initialBalanceInput.trim().length > 0 && stepTwoIssue)) && (
                                <p className="text-xs text-red-500">
                                    {fieldErrors.initial_balance || stepTwoIssue}
                                </p>
                            )}
                        </div>
                    </div>

                    <Button
                        className={`h-11 w-full ${DISABLED_BUTTON_CURSOR_CLASS}`}
                        type="submit"
                        disabled={!canSubmit}
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
                </form>
            )}
        </AuthFormCard>
    );
}
