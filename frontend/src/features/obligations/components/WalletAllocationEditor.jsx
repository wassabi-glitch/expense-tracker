import { Plus, Trash2, WalletCards } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { formatAmountInput, formatUzs, parseAmountInput } from "@/lib/format";

export function walletBalance(wallet) {
  return Number(wallet?.current_balance ?? wallet?.balance ?? 0);
}

export function normalizeWalletAllocations(rows = []) {
  return rows
    .map((row) => ({
      wallet_id: Number(row.wallet_id),
      amount: parseAmountInput(row.amount),
    }))
    .filter((row) => row.wallet_id && row.amount > 0);
}

export function walletAllocationTotal(rows = []) {
  return normalizeWalletAllocations(rows).reduce((sum, row) => sum + row.amount, 0);
}

export function defaultWalletAllocation(wallets = [], amount = "") {
  const wallet = wallets.find((item) => item.is_default) || wallets[0];
  return [{ wallet_id: wallet?.id ? String(wallet.id) : "", amount }];
}

export function WalletAllocationEditor({
  wallets = [],
  rows = [],
  onChange,
  expectedAmount = 0,
  disabled = false,
  title = "Wallet allocation",
  description = "Split this payment across one or more wallets.",
  requireExact = true,
  checkBalance = true,
}) {
  const activeWallets = wallets.filter((wallet) => wallet.is_active !== false);
  const total = walletAllocationTotal(rows);
  const expected = Number(expectedAmount || 0);
  const isBalanced = expected > 0 && total === expected;
  const isOver = expected > 0 && total > expected;

  const updateRow = (index, patch) => {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  };

  const removeRow = (index) => {
    onChange(rows.filter((_, rowIndex) => rowIndex !== index));
  };

  return (
    <div className="space-y-4 rounded-lg border border-border bg-muted/15 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <WalletCards className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold">{title}</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
        <Badge
          variant={isBalanced || (!requireExact && total > 0) ? "default" : "secondary"}
          className={cn("shrink-0 rounded-md px-3 py-1", isOver && "bg-destructive text-destructive-foreground")}
        >
          {formatUzs(total)} / {formatUzs(expected)} UZS
        </Badge>
      </div>

      <div className="space-y-3">
        {rows.map((row, index) => {
          const selectedWallet = activeWallets.find((wallet) => String(wallet.id) === String(row.wallet_id));
          const rowAmount = parseAmountInput(row.amount);
          const insufficient = checkBalance && selectedWallet && rowAmount > walletBalance(selectedWallet);

          return (
            <div key={`${row.wallet_id || "new"}-${index}`} className="grid gap-3 rounded-lg border border-border/70 bg-background p-4 sm:grid-cols-[minmax(0,1fr)_190px_auto]">
              <div className="space-y-1">
                <Label className="text-xs">Wallet</Label>
                <Select
                  value={row.wallet_id ? String(row.wallet_id) : undefined}
                  onValueChange={(value) => updateRow(index, { wallet_id: value })}
                  disabled={disabled}
                >
                  <SelectTrigger className="h-11 rounded-md">
                    <SelectValue placeholder="Select wallet" />
                  </SelectTrigger>
                  <SelectContent>
                    {activeWallets.map((wallet) => (
                      <SelectItem key={wallet.id} value={String(wallet.id)}>
                        {wallet.name} - {formatUzs(walletBalance(wallet))} UZS
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label className="text-xs">Amount</Label>
                <Input
                  value={row.amount}
                  onChange={(event) => updateRow(index, { amount: formatAmountInput(event.target.value, 15) })}
                  placeholder="0"
                  inputMode="numeric"
                  disabled={disabled}
                  className="h-11 rounded-md"
                />
              </div>

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-11 w-11 self-end rounded-md"
                onClick={() => removeRow(index)}
                disabled={disabled || rows.length === 1}
              >
                <Trash2 className="h-4 w-4" />
              </Button>

              {insufficient ? (
                <p className="text-xs font-medium text-destructive sm:col-span-3">
                  This wallet balance is lower than this allocation.
                </p>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          className="rounded-md"
          onClick={() => onChange([...rows, { wallet_id: "", amount: "" }])}
          disabled={disabled}
        >
          <Plus className="mr-2 h-4 w-4" />
          Add wallet
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="rounded-md"
          onClick={() => onChange(defaultWalletAllocation(activeWallets, formatAmountInput(String(expected || ""))))}
          disabled={disabled || !activeWallets.length || !expected}
        >
          Fill default wallet
        </Button>
      </div>
    </div>
  );
}
