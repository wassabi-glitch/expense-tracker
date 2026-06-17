import * as React from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { ArrowDownLeft, ArrowUpRight, History, Wallet as WalletIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { getWalletTransactions } from "@/lib/api";
import { formatDisplayDate, formatDisplayDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { getWalletStyle } from "@/lib/walletStyles";

const PAGE_SIZE = 50;
const TITLE_LIMIT = 32;

const EVENT_TYPE_LABELS = {
  EXPENSE: "Expense",
  INCOME: "Income",
  TRANSFER: "Transfer",
  REFUND: "Refund",
  ADJUSTMENT: "Adjustment",
  DEBT_SETTLEMENT: "Debt",
  NEUTRAL_FLOW: "System",
};

function truncateTitle(title) {
  const value = String(title || "Transaction").trim() || "Transaction";
  if (value.length <= TITLE_LIMIT) return value;
  return `${value.slice(0, TITLE_LIMIT - 3)}...`;
}

function getLoadedCount(pages) {
  return pages.reduce((sum, page) => sum + (Array.isArray(page?.items) ? page.items.length : 0), 0);
}

function TransactionDirectionIcon({ amount }) {
  const isInflow = Number(amount) > 0;
  const Icon = isInflow ? ArrowDownLeft : ArrowUpRight;
  return (
    <span
      className={cn(
        "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
        isInflow ? "bg-emerald-500/10 text-emerald-600" : "bg-rose-500/10 text-rose-600"
      )}
    >
      <Icon className="h-4 w-4" />
    </span>
  );
}

function TransactionRow({ transaction, appLang, t }) {
  const amount = Number(transaction.amount || 0);
  const isInflow = amount > 0;
  const fullTitle = String(transaction.title || "Transaction").trim() || "Transaction";
  const visibleTitle = truncateTitle(fullTitle);
  const eventLabel = t(`wallets.transactionTypes.${String(transaction.event_type || "").toLowerCase()}`, {
    defaultValue: EVENT_TYPE_LABELS[transaction.event_type] || "System",
  });

  return (
    <div className="flex min-w-0 items-start gap-3 rounded-md border border-border/50 bg-background/70 p-3">
      <TransactionDirectionIcon amount={amount} />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <p
            className="min-w-0 flex-1 truncate text-sm font-semibold leading-5 text-foreground"
            title={fullTitle}
          >
            {visibleTitle}
          </p>
          <div
            className={cn(
              "shrink-0 whitespace-nowrap text-right text-sm font-black tabular-nums",
              isInflow ? "text-emerald-600" : "text-rose-600"
            )}
          >
            <CurrencyAmount
              value={Math.abs(amount)}
              prefix={isInflow ? "+" : "-"}
              format="compact"
              includeCurrency={false}
              tooltip="always"
            />
          </div>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs font-medium text-muted-foreground">
          <span>{formatDisplayDate(transaction.date, appLang)}</span>
          <span className="text-muted-foreground/40">/</span>
          <span>{eventLabel}</span>
        </div>
        <p className="truncate text-[11px] font-medium text-muted-foreground/60">
          {t("wallets.transactionLogged", { defaultValue: "logged" })}{" "}
          {formatDisplayDateTime(transaction.created_at, appLang)}
        </p>
      </div>
    </div>
  );
}

export function WalletTransactionsDialog({ isOpen, onOpenChange, wallet }) {
  const { t, i18n } = useTranslation();
  const [direction, setDirection] = React.useState("all");
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const walletStyle = getWalletStyle(wallet?.color);

  React.useEffect(() => {
    if (isOpen) setDirection("all");
  }, [isOpen, wallet?.id]);

  const query = useInfiniteQuery({
    queryKey: ["wallet-transactions", wallet?.id, direction],
    enabled: isOpen && Boolean(wallet?.id),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      getWalletTransactions(wallet.id, {
        direction,
        limit: PAGE_SIZE,
        offset: pageParam,
      }),
    getNextPageParam: (lastPage, pages) => {
      const loaded = getLoadedCount(pages);
      const total = Number(lastPage?.total || 0);
      if (!Array.isArray(lastPage?.items) || lastPage.items.length === 0) return undefined;
      return loaded < total ? loaded : undefined;
    },
  });

  const pages = query.data?.pages || [];
  const transactions = pages.flatMap((page) => (Array.isArray(page?.items) ? page.items : []));
  const total = Number(pages[0]?.total || 0);
  const isInitialLoading = query.isLoading || (query.isFetching && transactions.length === 0);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] flex-col overflow-hidden p-0 sm:max-w-xl">
        <DialogHeader className="border-b border-border/50 p-5 pr-12">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className={cn(
                "flex h-11 w-11 shrink-0 items-center justify-center rounded-md shadow-sm",
                walletStyle.className
              )}
            >
              <WalletIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <DialogTitle className="truncate text-lg font-black">
                {wallet?.name || t("wallets.label", { defaultValue: "Wallet" })}
              </DialogTitle>
              <DialogDescription>
                {t("wallets.transactionsTitle", { defaultValue: "Transactions" })}
                {total > 0 ? ` (${total})` : ""}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Tabs value={direction} onValueChange={setDirection} className="min-h-0 flex-1 gap-0">
          <div className="border-b border-border/50 px-5 py-3">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="all">{t("wallets.transactionsAll", { defaultValue: "All" })}</TabsTrigger>
              <TabsTrigger value="in">{t("wallets.transactionsIn", { defaultValue: "In" })}</TabsTrigger>
              <TabsTrigger value="out">{t("wallets.transactionsOut", { defaultValue: "Out" })}</TabsTrigger>
            </TabsList>
          </div>

          {["all", "in", "out"].map((tab) => (
            <TabsContent key={tab} value={tab} className="min-h-0 flex-1 overflow-hidden">
              <div className="flex max-h-[55vh] min-h-[260px] flex-col overflow-y-auto p-5">
                {isInitialLoading ? (
                  <div className="flex flex-1 items-center justify-center">
                    <LoadingSpinner className="h-7 w-7 text-primary" />
                  </div>
                ) : query.isError ? (
                  <div className="flex flex-1 items-center justify-center text-center text-sm font-medium text-destructive">
                    {t("wallets.transactionsError", { defaultValue: "Could not load transactions." })}
                  </div>
                ) : transactions.length === 0 ? (
                  <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
                    <History className="h-8 w-8 text-muted-foreground/40" />
                    <p className="text-sm font-medium text-muted-foreground">
                      {t("wallets.transactionsEmpty", { defaultValue: "No transactions yet." })}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {transactions.map((transaction) => (
                      <TransactionRow
                        key={transaction.id}
                        transaction={transaction}
                        appLang={appLang}
                        t={t}
                      />
                    ))}
                    {query.hasNextPage ? (
                      <Button
                        type="button"
                        variant="outline"
                        className="mt-3 w-full"
                        disabled={query.isFetchingNextPage}
                        onClick={() => query.fetchNextPage()}
                      >
                        {query.isFetchingNextPage ? (
                          <LoadingSpinner size="sm" />
                        ) : (
                          t("common.loadMore", { defaultValue: "Load more" })
                        )}
                      </Button>
                    ) : null}
                  </div>
                )}
              </div>
            </TabsContent>
          ))}
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
