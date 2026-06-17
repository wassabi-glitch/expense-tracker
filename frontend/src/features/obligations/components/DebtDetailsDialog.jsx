import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  ClipboardList,
  Landmark,
  MinusCircle,
  PlusCircle,
  RefreshCcw,
  Scale,
  ShieldAlert,
  WalletCards,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { getWallets } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatAmountInput, formatDisplayDate, formatDisplayDateTime, formatUzs, parseAmountInput } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import { useDebtDetailsQuery } from "../hooks/useDebtsQueries";
import {
  useAddChargeMutation,
  useAdjustDebtBalanceMutation,
  useForgiveDebtAmountMutation,
  useRecordDebtPaymentForDebtMutation,
  useReverseDebtLedgerEntryMutation,
  useSettleDebtMutation,
} from "../hooks/useDebtsMutations";
import {
  defaultWalletAllocation,
  normalizeWalletAllocations,
  WalletAllocationEditor,
  walletAllocationTotal,
} from "./WalletAllocationEditor";

function actionByKind(actions = [], kind) {
  return actions.find((action) => action.action_kind === kind);
}

function actionAllowed(actions = [], kind) {
  return actionByKind(actions, kind)?.allowed === true;
}

function activityIcon(kind) {
  if (kind === "PAYMENT") return Banknote;
  if (kind === "CHARGE") return PlusCircle;
  if (kind === "FORGIVENESS") return MinusCircle;
  if (kind === "ADJUSTMENT") return Scale;
  if (kind === "REVERSAL") return RefreshCcw;
  return ClipboardList;
}

function activityColor(kind) {
  if (kind === "PAYMENT") return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
  if (kind === "CHARGE") return "text-amber-500 bg-amber-500/10 border-amber-500/20";
  if (kind === "FORGIVENESS") return "text-sky-500 bg-sky-500/10 border-sky-500/20";
  if (kind === "ADJUSTMENT") return "text-violet-500 bg-violet-500/10 border-violet-500/20";
  if (kind === "REVERSAL") return "text-muted-foreground bg-muted border-border";
  return "text-primary bg-primary/10 border-primary/20";
}

function Metric({ label, value, tone = "default" }) {
  return (
    <div className="rounded-lg border border-border bg-muted/15 p-3">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={cn("mt-2 text-xl font-semibold tabular-nums", tone === "danger" && "text-destructive", tone === "success" && "text-emerald-500")}>
        {value}
      </p>
    </div>
  );
}

function PaymentForm({ debt, wallets, onClose }) {
  const mutation = useRecordDebtPaymentForDebtMutation();
  const [date, setDate] = useState(toISODateInTimeZone());
  const [note, setNote] = useState("");
  const [walletAllocations, setWalletAllocations] = useState(() => defaultWalletAllocation(wallets));
  const defaultWalletId = wallets.find((wallet) => wallet.is_default)?.id || wallets[0]?.id;
  const total = walletAllocationTotal(walletAllocations);
  const overpay = total > Number(debt?.remaining_amount || 0);
  const canSubmit = total > 0 && !overpay && !mutation.isPending;

  useEffect(() => {
    if (!defaultWalletId) return;
    setWalletAllocations((rows) => (rows.some((row) => row.wallet_id) ? rows : defaultWalletAllocation(wallets)));
  }, [defaultWalletId]);

  const submit = async () => {
    if (!canSubmit) return;
    await mutation.mutateAsync({
        debtId: debt.id,
        payload: {
        amount: total,
        date,
        note: note || null,
        wallet_allocations: normalizeWalletAllocations(walletAllocations),
      },
    });
    onClose();
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_190px]">
        <div className="space-y-1">
          <Label>Payment amount</Label>
          <Input value={`${formatUzs(total)} UZS`} readOnly className="h-11 rounded-md text-base" />
          <p className="text-xs text-muted-foreground">This total is calculated from the wallet rows below.</p>
        </div>
        <div className="space-y-1">
          <Label>Date</Label>
          <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="h-11 rounded-md text-base" />
        </div>
      </div>
      <WalletAllocationEditor
        wallets={wallets}
        rows={walletAllocations}
        onChange={setWalletAllocations}
        expectedAmount={total}
        disabled={mutation.isPending}
        requireExact={false}
      />
      <div className="space-y-1">
        <Label>Note</Label>
        <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Receipt, branch, agreement note..." className="min-h-24 rounded-md" />
      </div>
      {overpay ? <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm font-medium text-destructive">Payment exceeds remaining balance.</p> : null}
      <Button className="h-11 w-full rounded-md text-base" disabled={!canSubmit} onClick={submit}>
        <WalletCards className="mr-2 h-4 w-4" />
        Record payment
      </Button>
    </div>
  );
}

function ChargeForm({ debt, onClose }) {
  const mutation = useAddChargeMutation();
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const amountValue = parseAmountInput(amount);

  const submit = async () => {
    if (amountValue <= 0) return;
    await mutation.mutateAsync({
      debtId: debt.id,
      payload: {
        amount: amountValue,
        reason: reason || null,
      },
    });
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label>Charge amount</Label>
        <Input value={amount} onChange={(event) => setAmount(formatAmountInput(event.target.value, 15))} inputMode="numeric" placeholder="0" className="rounded-md" />
      </div>
      <div className="space-y-1">
        <Label>Reason</Label>
        <Input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Interest, penalty, service fee" className="rounded-md" />
      </div>
      <Button className="w-full rounded-md" disabled={amountValue <= 0 || mutation.isPending} onClick={submit}>
        <PlusCircle className="mr-2 h-4 w-4" />
        Add charge
      </Button>
    </div>
  );
}

function ForgivenessForm({ debt, onClose }) {
  const mutation = useForgiveDebtAmountMutation();
  const [amount, setAmount] = useState(formatAmountInput(String(debt?.remaining_amount || "")));
  const [note, setNote] = useState("");
  const amountValue = parseAmountInput(amount);

  const submit = async () => {
    if (amountValue <= 0) return;
    await mutation.mutateAsync({
      debtId: debt.id,
      payload: {
        amount: amountValue,
        date: toISODateInTimeZone(),
        note: note || null,
      },
    });
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 p-3 text-sm text-sky-700 dark:text-sky-300">
        Forgiveness reduces the obligation without moving wallet money. Use it only when the counterparty truly forgives part of the balance.
      </div>
      <div className="space-y-1">
        <Label>Forgiven amount</Label>
        <Input value={amount} onChange={(event) => setAmount(formatAmountInput(event.target.value, 15))} inputMode="numeric" className="rounded-md" />
      </div>
      <div className="space-y-1">
        <Label>Note</Label>
        <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Why this amount is forgiven" className="min-h-20 rounded-md" />
      </div>
      <Button className="w-full rounded-md" disabled={amountValue <= 0 || amountValue > Number(debt?.remaining_amount || 0) || mutation.isPending} onClick={submit}>
        <MinusCircle className="mr-2 h-4 w-4" />
        Record forgiveness
      </Button>
    </div>
  );
}

function SettlementForm({ debt, wallets, onClose }) {
  const mutation = useSettleDebtMutation();
  const remaining = Number(debt?.remaining_amount || 0);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [discount, setDiscount] = useState("");
  const [note, setNote] = useState("");
  const [walletAllocations, setWalletAllocations] = useState(() => defaultWalletAllocation(wallets));
  const defaultWalletId = wallets.find((wallet) => wallet.is_default)?.id || wallets[0]?.id;
  const payment = parseAmountInput(paymentAmount);
  const settlementDiscount = parseAmountInput(discount);
  const total = payment + settlementDiscount;
  const walletTotal = walletAllocationTotal(walletAllocations);
  const canSubmit = total === remaining && walletTotal === payment && !mutation.isPending;

  useEffect(() => {
    if (!defaultWalletId) return;
    setWalletAllocations((rows) => (rows.some((row) => row.wallet_id) ? rows : defaultWalletAllocation(wallets)));
  }, [defaultWalletId]);

  const submit = async () => {
    if (!canSubmit) return;
    await mutation.mutateAsync({
      debtId: debt.id,
      payload: {
        payment_amount: payment,
        settlement_discount: settlementDiscount,
        date: toISODateInTimeZone(),
        note: note || null,
        wallet_allocations: normalizeWalletAllocations(walletAllocations),
      },
    });
    onClose();
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-300">
        Settlement closes a formal debt by combining a real payment and an agreed discount. Payment + discount must equal the remaining balance.
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <Label>Payment now</Label>
          <Input value={paymentAmount} onChange={(event) => setPaymentAmount(formatAmountInput(event.target.value, 15))} inputMode="numeric" className="h-11 rounded-md text-base" />
        </div>
        <div className="space-y-1">
          <Label>Discount / write-down</Label>
          <Input value={discount} onChange={(event) => setDiscount(formatAmountInput(event.target.value, 15))} inputMode="numeric" className="h-11 rounded-md text-base" />
        </div>
      </div>
      <WalletAllocationEditor wallets={wallets} rows={walletAllocations} onChange={setWalletAllocations} expectedAmount={payment} disabled={mutation.isPending} />
      <div className="space-y-1">
        <Label>Note</Label>
        <Textarea value={note} onChange={(event) => setNote(event.target.value)} className="min-h-24 rounded-md" />
      </div>
      <div className={cn("rounded-lg border p-4 text-sm", total === remaining ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "border-border bg-muted/15 text-muted-foreground")}>
        {formatUzs(total)} / {formatUzs(remaining)} UZS accounted for
      </div>
      <Button className="h-11 w-full rounded-md text-base" disabled={!canSubmit} onClick={submit}>
        <CheckCircle2 className="mr-2 h-4 w-4" />
        Settle and close
      </Button>
    </div>
  );
}

function BalanceAdjustmentForm({ debt, onClose }) {
  const mutation = useAdjustDebtBalanceMutation();
  const [confirmedBalance, setConfirmedBalance] = useState(formatAmountInput(String(debt?.remaining_amount || "")));
  const [note, setNote] = useState("");
  const value = parseAmountInput(confirmedBalance);

  const submit = async () => {
    await mutation.mutateAsync({
      debtId: debt.id,
      payload: {
        confirmed_balance: value,
        date: toISODateInTimeZone(),
        note: note || null,
      },
    });
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-violet-500/30 bg-violet-500/10 p-3 text-sm text-violet-700 dark:text-violet-300">
        Use this when a statement or counterparty confirms the real balance differs from your app balance.
      </div>
      <div className="space-y-1">
        <Label>Confirmed balance</Label>
        <Input value={confirmedBalance} onChange={(event) => setConfirmedBalance(formatAmountInput(event.target.value, 15))} inputMode="numeric" className="rounded-md" />
      </div>
      <div className="space-y-1">
        <Label>Note</Label>
        <Textarea value={note} onChange={(event) => setNote(event.target.value)} className="min-h-20 rounded-md" />
      </div>
      <Button className="w-full rounded-md" disabled={mutation.isPending} onClick={submit}>
        <Scale className="mr-2 h-4 w-4" />
        Adjust balance
      </Button>
    </div>
  );
}

function ActionPanel({ mode, debt, wallets, onClose }) {
  if (mode === "payment") return <PaymentForm debt={debt} wallets={wallets} onClose={onClose} />;
  if (mode === "charge") return <ChargeForm debt={debt} onClose={onClose} />;
  if (mode === "forgive") return <ForgivenessForm debt={debt} onClose={onClose} />;
  if (mode === "settle") return <SettlementForm debt={debt} wallets={wallets} onClose={onClose} />;
  if (mode === "adjust") return <BalanceAdjustmentForm debt={debt} onClose={onClose} />;
  return null;
}

export function DebtDetailsDialog({ debt, open, onOpenChange, appLang = "en" }) {
  const { t } = useTranslation();
  const detailsQuery = useDebtDetailsQuery(debt?.id, { enabled: open && !!debt?.id });
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets, enabled: open });
  const reverseMutation = useReverseDebtLedgerEntryMutation();
  const [mode, setMode] = useState(null);

  const details = detailsQuery.data;
  const currentDebt = details?.debt || debt;
  const wallets = useMemo(() => (Array.isArray(walletsQuery.data) ? walletsQuery.data : []), [walletsQuery.data]);
  const actions = details?.actions || [];
  const activity = details?.activity || [];
  const total = Number(currentDebt?.initial_amount || 0) + Number(currentDebt?.total_charges || 0);
  const paid = Math.max(total - Number(currentDebt?.remaining_amount || 0), 0);
  const progress = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;

  const canPayment = actionAllowed(actions, "RECORD_PAYMENT");
  const canCharge = actionAllowed(actions, "ADD_CHARGE");
  const canForgivePartial = actionAllowed(actions, "FORGIVE_PARTIAL") || actionAllowed(actions, "FORGIVE_FULL");
  const canSettle = actionAllowed(actions, "SETTLE");
  const canAdjust = actionAllowed(actions, "ADJUST_BALANCE");

  const closePanel = () => {
    setMode(null);
  };

  return (
    <Dialog open={open} onOpenChange={(value) => { if (!value) setMode(null); onOpenChange(value); }}>
      <DialogContent className="max-w-[92rem] p-0">
        <DialogHeader className="border-b border-border px-5 py-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <DialogTitle className="flex items-center gap-2">
                <Landmark className="h-5 w-5 text-primary" />
                {currentDebt?.description || currentDebt?.counterparty_name || "Debt details"}
              </DialogTitle>
              <DialogDescription>
                {currentDebt?.counterparty_name} - {currentDebt?.product_kind || currentDebt?.origin_kind || "Debt"} - {currentDebt?.status}
              </DialogDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="rounded-md">{currentDebt?.debt_type === "OWING" ? "I owe" : "Owed to me"}</Badge>
              <Badge variant={currentDebt?.status === "ACTIVE" ? "default" : "secondary"} className="rounded-md">{currentDebt?.status}</Badge>
            </div>
          </div>
        </DialogHeader>

        <div className="grid max-h-[calc(100vh-9rem)] overflow-hidden lg:grid-cols-[minmax(0,1fr)_520px]">
          <div className="overflow-y-auto p-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <Metric label="Remaining" value={`${formatUzs(currentDebt?.remaining_amount)} UZS`} tone={currentDebt?.debt_type === "OWING" ? "danger" : "success"} />
              <Metric label="Paid / cleared" value={`${formatUzs(paid)} UZS`} tone="success" />
              <Metric label="Charges" value={`${formatUzs(currentDebt?.total_charges || 0)} UZS`} />
            </div>

            <div className="mt-4 rounded-lg border border-border bg-muted/15 p-4">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="font-medium">Balance progress</span>
                <span className="font-semibold tabular-nums">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
              <div className="mt-2 flex justify-between text-xs text-muted-foreground">
                <span>Opened {formatDisplayDate(currentDebt?.date, appLang)}</span>
                <span>{currentDebt?.expected_return_date ? `Due ${formatDisplayDate(currentDebt.expected_return_date, appLang)}` : "No due date"}</span>
              </div>
            </div>

            <div className="mt-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Storyline</h3>
                {detailsQuery.isLoading ? <span className="text-xs text-muted-foreground">Loading...</span> : null}
              </div>
              <div className="relative space-y-3">
                {activity.length ? <div className="absolute bottom-5 left-[17px] top-5 w-px bg-border" /> : null}
                {activity.map((item) => {
                  const Icon = activityIcon(item.kind);
                  const reversible = item.reversal?.allowed === true;
                  return (
                    <div key={item.ledger_entry_id} className="relative grid grid-cols-[36px_minmax(0,1fr)] gap-3">
                      <div className={cn("relative z-10 flex h-9 w-9 items-center justify-center rounded-md border", activityColor(item.kind))}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="grid gap-3 rounded-lg border border-border bg-card p-4 sm:grid-cols-[minmax(0,1fr)_auto]">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold">{item.title}</p>
                            <Badge variant="outline" className="rounded-md">{item.kind}</Badge>
                            {item.event_subtype ? <Badge variant="secondary" className="rounded-md">{item.event_subtype}</Badge> : null}
                          </div>
                          <p className="mt-1 text-sm text-muted-foreground">{item.description || "No note"}</p>
                          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                            <span>
                              <span className="font-medium text-foreground/70">Date:</span>{" "}
                              {formatDisplayDate(item.entry_date, appLang)}
                            </span>
                            <span>
                              <span className="font-medium text-foreground/70">Recorded:</span>{" "}
                              {formatDisplayDateTime(item.created_at, appLang)}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col items-start gap-2 sm:items-end">
                          <p className={cn("font-semibold tabular-nums", item.amount_delta < 0 ? "text-emerald-500" : "text-foreground")}>
                            {item.amount_delta > 0 ? "+" : ""}{formatUzs(item.amount_delta)} UZS
                          </p>
                          <p className="text-xs text-muted-foreground">Balance {formatUzs(item.balance_after)} UZS</p>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 rounded-md"
                            disabled={!reversible || reverseMutation.isPending}
                            title={t("debts.reversal.reverseWarning", {
                              defaultValue: "This will restore app wallet money only when the real payment failed, was cancelled, refunded, or was recorded by mistake.",
                            })}
                            onClick={() => {
                              const confirmed = window.confirm(t("debts.reversal.reverseWarning", {
                                defaultValue: "This will restore app wallet money only when the real payment failed, was cancelled, refunded, or was recorded by mistake.",
                              }));
                              if (!confirmed) return;
                              reverseMutation.mutate({ debtId: currentDebt.id, entryId: item.ledger_entry_id, payload: { note: "Reversed from debt details" } });
                            }}
                          >
                            <RefreshCcw className="mr-2 h-3.5 w-3.5" />
                            Reverse
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
                {!activity.length && !detailsQuery.isLoading ? (
                  <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                    No debt activity yet.
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <aside className="overflow-y-auto border-t border-border bg-muted/10 p-6 lg:border-l lg:border-t-0">
            <div className="space-y-3">
              <Button className="h-11 w-full justify-start rounded-md" disabled={!canPayment} onClick={() => setMode(mode === "payment" ? null : "payment")}>
                <Banknote className="mr-2 h-4 w-4" />
                Record payment
              </Button>
              <Button variant="outline" className="h-11 w-full justify-start rounded-md" disabled={!canCharge} onClick={() => setMode(mode === "charge" ? null : "charge")}>
                <PlusCircle className="mr-2 h-4 w-4" />
                Add charge
              </Button>
              <Button variant="outline" className="h-11 w-full justify-start rounded-md" disabled={!canForgivePartial} onClick={() => setMode(mode === "forgive" ? null : "forgive")}>
                <MinusCircle className="mr-2 h-4 w-4" />
                Forgive balance
              </Button>
              <Button variant="outline" className="h-11 w-full justify-start rounded-md" disabled={!canSettle} onClick={() => setMode(mode === "settle" ? null : "settle")}>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Formal settlement
              </Button>
              <Button variant="outline" className="h-11 w-full justify-start rounded-md" disabled={!canAdjust} onClick={() => setMode(mode === "adjust" ? null : "adjust")}>
                <Scale className="mr-2 h-4 w-4" />
                Correct balance
              </Button>
            </div>

            {mode ? (
              <div className="mt-6 rounded-lg border border-border bg-background p-5">
                <ActionPanel mode={mode} debt={currentDebt} wallets={wallets} onClose={closePanel} />
              </div>
            ) : (
              <div className="mt-5 space-y-3 rounded-lg border border-border bg-background p-4">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-semibold">Policy-aware actions</p>
                    <p className="mt-1 text-xs text-muted-foreground">Unavailable actions are blocked by debt status, debt type, or formal/informal policy rules.</p>
                  </div>
                </div>
                {actions.filter((action) => !action.allowed).slice(0, 4).map((action) => (
                  <div key={action.action_kind} className="flex items-start gap-2 rounded-md bg-muted/30 p-2 text-xs text-muted-foreground">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5" />
                    <span>{action.action_kind}: {action.reason_code || "not available"}</span>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </DialogContent>
    </Dialog>
  );
}
