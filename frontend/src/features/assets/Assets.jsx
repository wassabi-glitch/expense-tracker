import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  Gift,
  PackageOpen,
  Pencil,
  Plus,
  Search,
  ShieldAlert,
  Wallet,
} from "lucide-react";

import { getWallets } from "@/lib/api";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useDebounce } from "@/hooks/useDebounce";
import { localizeApiError } from "@/lib/errorMessages";
import { formatAmountInput, formatDisplayDate, parseAmountInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useAssetsQuery } from "./hooks/useAssetsQuery";
import { useAssetMutations } from "./hooks/useAssetMutations";

const PAGE_SIZE = 12;
const STATUS_OPTIONS = [
  { value: "all", label: "All" },
  { value: "owned", label: "Owned" },
  { value: "sold", label: "Sold" },
  { value: "gifted", label: "Gifted" },
  { value: "disposed", label: "Disposed" },
  { value: "lost", label: "Lost" },
];

const CLOSE_ACTIONS = [
  { key: "gift", status: "gifted", label: "Gift", icon: Gift },
  { key: "dispose", status: "disposed", label: "Dispose", icon: PackageOpen },
  { key: "lost", status: "lost", label: "Lost", icon: ShieldAlert },
];

const defaultCreateForm = {
  title: "",
  description: "",
  purchaseValue: "",
  currentValue: "",
  originEventId: "",
};

const defaultEditForm = {
  title: "",
  description: "",
  currentValue: "",
  status: "owned",
};

const defaultSellForm = {
  saleValue: "",
  soldDate: "",
  note: "",
  walletMode: "none",
  destinationWalletId: "",
  walletAllocations: [{ wallet_id: "", amount: "" }],
};

const defaultCloseForm = {
  closedDate: "",
  note: "",
};

function statusTone(status) {
  switch (String(status || "").toLowerCase()) {
    case "sold":
      return "border-emerald-500/25 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    case "gifted":
      return "border-sky-500/25 bg-sky-500/10 text-sky-600 dark:text-sky-400";
    case "disposed":
      return "border-amber-500/25 bg-amber-500/10 text-amber-600 dark:text-amber-400";
    case "lost":
      return "border-rose-500/25 bg-rose-500/10 text-rose-600 dark:text-rose-400";
    default:
      return "border-primary/25 bg-primary/10 text-primary";
  }
}

function SummaryStat({ title, value, hint }) {
  return (
    <Card className="shadow-sm">
      <CardContent className="p-5">
        <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{title}</p>
        <p className="mt-2 text-2xl font-bold tracking-tight">{value}</p>
        {hint ? <p className="mt-2 text-ui-desc text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}

function AssetFormDialog({
  open,
  onOpenChange,
  title,
  submitLabel,
  form,
  setForm,
  onSubmit,
  isPending,
  error,
  showStatus = false,
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 pt-1">
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Title</label>
            <Input
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              className="rounded-2xl"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Description</label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              className="min-h-24 rounded-2xl"
            />
          </div>
          {"purchaseValue" in form ? (
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Purchase value</label>
              <Input
                inputMode="numeric"
                value={form.purchaseValue}
                onChange={(e) => setForm((prev) => ({ ...prev, purchaseValue: formatAmountInput(e.target.value) }))}
                className="rounded-2xl"
              />
            </div>
          ) : null}
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Current value</label>
            <Input
              inputMode="numeric"
              value={form.currentValue}
              onChange={(e) => setForm((prev) => ({ ...prev, currentValue: formatAmountInput(e.target.value) }))}
              className="rounded-2xl"
            />
          </div>
          {"originEventId" in form ? (
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Origin expense ID</label>
              <Input
                inputMode="numeric"
                value={form.originEventId}
                onChange={(e) => setForm((prev) => ({ ...prev, originEventId: e.target.value.replace(/\D/g, "") }))}
                className="rounded-2xl"
                placeholder="Optional"
              />
            </div>
          ) : null}
          {showStatus ? (
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Status</label>
              <Select value={form.status} onValueChange={(value) => setForm((prev) => ({ ...prev, status: value }))}>
                <SelectTrigger className="rounded-2xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.filter((option) => option.value !== "all").map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={isPending}>
            {isPending ? <LoadingSpinner size="sm" /> : submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AssetSellDialog({
  open,
  onOpenChange,
  form,
  setForm,
  wallets,
  onSubmit,
  isPending,
  error,
}) {
  const allocationTotal = useMemo(
    () =>
      (form.walletAllocations || []).reduce(
        (sum, item) => sum + (parseAmountInput(item.amount) || 0),
        0
      ),
    [form.walletAllocations]
  );
  const saleValue = parseAmountInput(form.saleValue) || 0;

  const updateAllocation = (index, field, value) => {
    setForm((prev) => ({
      ...prev,
      walletAllocations: prev.walletAllocations.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item
      ),
    }));
  };

  const addAllocation = () => {
    setForm((prev) => ({
      ...prev,
      walletAllocations: [...prev.walletAllocations, { wallet_id: "", amount: "" }],
    }));
  };

  const removeAllocation = (index) => {
    setForm((prev) => ({
      ...prev,
      walletAllocations: prev.walletAllocations.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sell asset</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 pt-1">
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Sale value</label>
            <Input
              inputMode="numeric"
              value={form.saleValue}
              onChange={(e) => setForm((prev) => ({ ...prev, saleValue: formatAmountInput(e.target.value) }))}
              className="rounded-2xl"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Sold date</label>
            <Input
              type="date"
              value={form.soldDate}
              onChange={(e) => setForm((prev) => ({ ...prev, soldDate: e.target.value }))}
              className="rounded-2xl"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Wallet handling</label>
            <Select value={form.walletMode} onValueChange={(value) => setForm((prev) => ({ ...prev, walletMode: value }))}>
              <SelectTrigger className="rounded-2xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No wallet inflow</SelectItem>
                <SelectItem value="single">Single wallet</SelectItem>
                <SelectItem value="multi">Split across wallets</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {form.walletMode === "single" ? (
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Destination wallet</label>
              <Select
                value={form.destinationWalletId}
                onValueChange={(value) => setForm((prev) => ({ ...prev, destinationWalletId: value }))}
              >
                <SelectTrigger className="rounded-2xl">
                  <SelectValue placeholder="Select wallet" />
                </SelectTrigger>
                <SelectContent>
                  {wallets.map((wallet) => (
                    <SelectItem key={wallet.id} value={String(wallet.id)}>
                      {wallet.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          {form.walletMode === "multi" ? (
            <div className="space-y-3 rounded-2xl border border-border bg-muted/20 p-3">
              {(form.walletAllocations || []).map((allocation, index) => (
                <div key={`${index}-${allocation.wallet_id}`} className="grid gap-2 sm:grid-cols-[1fr_160px_auto]">
                  <Select
                    value={allocation.wallet_id}
                    onValueChange={(value) => updateAllocation(index, "wallet_id", value)}
                  >
                    <SelectTrigger className="rounded-2xl">
                      <SelectValue placeholder="Select wallet" />
                    </SelectTrigger>
                    <SelectContent>
                      {wallets.map((wallet) => (
                        <SelectItem key={wallet.id} value={String(wallet.id)}>
                          {wallet.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    inputMode="numeric"
                    value={allocation.amount}
                    onChange={(e) => updateAllocation(index, "amount", formatAmountInput(e.target.value))}
                    className="rounded-2xl"
                    placeholder="Amount"
                  />
                  <Button
                    variant="outline"
                    className="rounded-2xl"
                    onClick={() => removeAllocation(index)}
                    disabled={form.walletAllocations.length <= 1}
                  >
                    Remove
                  </Button>
                </div>
              ))}
              <div className="flex items-center justify-between gap-3">
                <Button variant="outline" className="rounded-2xl" onClick={addAllocation}>
                  Add wallet split
                </Button>
                <p className={cn("text-sm", allocationTotal !== saleValue ? "text-amber-500" : "text-muted-foreground")}>
                  Split total: <CurrencyAmount value={allocationTotal} format="display" />
                </p>
              </div>
            </div>
          ) : null}
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Note</label>
            <Textarea
              value={form.note}
              onChange={(e) => setForm((prev) => ({ ...prev, note: e.target.value }))}
              className="min-h-20 rounded-2xl"
            />
          </div>
          {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={isPending}>
            {isPending ? <LoadingSpinner size="sm" /> : "Sell asset"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AssetCloseDialog({
  open,
  onOpenChange,
  title,
  form,
  setForm,
  onSubmit,
  isPending,
  error,
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 pt-1">
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Date</label>
            <Input
              type="date"
              value={form.closedDate}
              onChange={(e) => setForm((prev) => ({ ...prev, closedDate: e.target.value }))}
              className="rounded-2xl"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Note</label>
            <Textarea
              value={form.note}
              onChange={(e) => setForm((prev) => ({ ...prev, note: e.target.value }))}
              className="min-h-20 rounded-2xl"
            />
          </div>
          {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={isPending}>
            {isPending ? <LoadingSpinner size="sm" /> : title}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Assets() {
  const { t, i18n } = useTranslation();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [sellOpen, setSellOpen] = useState(false);
  const [closeAction, setCloseAction] = useState(null);

  const [createForm, setCreateForm] = useState(defaultCreateForm);
  const [editForm, setEditForm] = useState(defaultEditForm);
  const [sellForm, setSellForm] = useState(defaultSellForm);
  const [closeForm, setCloseForm] = useState(defaultCloseForm);

  const [createError, setCreateError] = useState("");
  const [editError, setEditError] = useState("");
  const [sellError, setSellError] = useState("");
  const [closeError, setCloseError] = useState("");

  const [selectedAsset, setSelectedAsset] = useState(null);

  const debouncedSearch = useDebounce(search, 250);
  const params = useMemo(
    () => ({
      limit: PAGE_SIZE,
      skip: (page - 1) * PAGE_SIZE,
      search: debouncedSearch.trim(),
      statusFilter: statusFilter === "all" ? "" : statusFilter,
    }),
    [debouncedSearch, page, statusFilter]
  );

  const assetsQuery = useAssetsQuery(params);
  const walletsQuery = useQuery({
    queryKey: ["wallets"],
    queryFn: getWallets,
    staleTime: 30_000,
  });
  const { createMutation, updateMutation, sellMutation, giftMutation, disposeMutation, lostMutation } = useAssetMutations();

  const assetsResponse = assetsQuery.data || { total: 0, items: [] };
  const assets = useMemo(
    () => (Array.isArray(assetsResponse.items) ? assetsResponse.items : []),
    [assetsResponse.items]
  );
  const totalPages = Math.max(1, Math.ceil((assetsResponse.total || 0) / PAGE_SIZE));
  const wallets = Array.isArray(walletsQuery.data) ? walletsQuery.data.filter((wallet) => wallet.is_active !== false) : [];

  const summary = useMemo(() => {
    const purchaseTotal = assets.reduce((sum, asset) => sum + Number(asset.purchase_value || 0), 0);
    const currentTotal = assets.reduce((sum, asset) => sum + Number(asset.current_value || 0), 0);
    const ownedCount = assets.filter((asset) => asset.status === "owned").length;
    const closedCount = assets.length - ownedCount;
    return { purchaseTotal, currentTotal, ownedCount, closedCount };
  }, [assets]);

  const resetCreate = () => {
    setCreateForm(defaultCreateForm);
    setCreateError("");
  };

  const openEdit = (asset) => {
    setSelectedAsset(asset);
    setEditForm({
      title: asset.title || "",
      description: asset.description || "",
      currentValue: formatAmountInput(String(asset.current_value || "")),
      status: asset.status || "owned",
    });
    setEditError("");
    setEditOpen(true);
  };

  const openSell = (asset) => {
    setSelectedAsset(asset);
    setSellForm({
      ...defaultSellForm,
      saleValue: formatAmountInput(String(asset.current_value || asset.purchase_value || "")),
    });
    setSellError("");
    setSellOpen(true);
  };

  const openClose = (asset, actionKey) => {
    setSelectedAsset(asset);
    setCloseAction(actionKey);
    setCloseForm(defaultCloseForm);
    setCloseError("");
  };

  const handleCreate = async () => {
    setCreateError("");
    const purchaseValue = parseAmountInput(createForm.purchaseValue);
    const currentValue = parseAmountInput(createForm.currentValue);
    if (!createForm.title.trim() || !purchaseValue || currentValue === 0 && createForm.currentValue === "") {
      setCreateError("Title, purchase value, and current value are required.");
      return;
    }
    try {
      await createMutation.mutateAsync({
        title: createForm.title.trim(),
        description: createForm.description.trim() || null,
        purchase_value: purchaseValue,
        current_value: currentValue || 0,
        origin_event_id: createForm.originEventId ? Number(createForm.originEventId) : null,
      });
      setCreateOpen(false);
      resetCreate();
    } catch (error) {
      setCreateError(localizeApiError(error.message, t) || error.message);
    }
  };

  const handleUpdate = async () => {
    if (!selectedAsset) return;
    setEditError("");
    const currentValue = parseAmountInput(editForm.currentValue);
    if (!editForm.title.trim() || currentValue === 0 && editForm.currentValue === "") {
      setEditError("Title and current value are required.");
      return;
    }
    try {
      await updateMutation.mutateAsync({
        id: selectedAsset.id,
        payload: {
          title: editForm.title.trim(),
          description: editForm.description.trim() || null,
          current_value: currentValue || 0,
          status: editForm.status,
        },
      });
      setEditOpen(false);
      setSelectedAsset(null);
    } catch (error) {
      setEditError(localizeApiError(error.message, t) || error.message);
    }
  };

  const handleSell = async () => {
    if (!selectedAsset) return;
    setSellError("");
    const saleValue = parseAmountInput(sellForm.saleValue);
    if (saleValue === 0 && sellForm.saleValue === "") {
      setSellError("Sale value is required.");
      return;
    }

    const payload = {
      sale_value: saleValue || 0,
      sold_date: sellForm.soldDate || null,
      note: sellForm.note.trim() || null,
    };

    if (sellForm.walletMode === "single") {
      if (!sellForm.destinationWalletId) {
        setSellError("Select a destination wallet.");
        return;
      }
      payload.destination_wallet_id = Number(sellForm.destinationWalletId);
    }

    if (sellForm.walletMode === "multi") {
      const walletAllocations = sellForm.walletAllocations
        .filter((item) => item.wallet_id && item.amount)
        .map((item) => ({
          wallet_id: Number(item.wallet_id),
          amount: parseAmountInput(item.amount) || 0,
        }));

      const total = walletAllocations.reduce((sum, item) => sum + item.amount, 0);
      if (!walletAllocations.length) {
        setSellError("Add at least one wallet allocation.");
        return;
      }
      if (total !== (saleValue || 0)) {
        setSellError("Wallet split total must match the sale value.");
        return;
      }
      payload.wallet_allocations = walletAllocations;
    }

    try {
      await sellMutation.mutateAsync({ id: selectedAsset.id, payload });
      setSellOpen(false);
      setSelectedAsset(null);
    } catch (error) {
      setSellError(localizeApiError(error.message, t) || error.message);
    }
  };

  const handleCloseAction = async () => {
    if (!selectedAsset || !closeAction) return;
    setCloseError("");
    const payload = {
      closed_date: closeForm.closedDate || null,
      note: closeForm.note.trim() || null,
    };

    try {
      if (closeAction === "gift") {
        await giftMutation.mutateAsync({ id: selectedAsset.id, payload });
      } else if (closeAction === "dispose") {
        await disposeMutation.mutateAsync({ id: selectedAsset.id, payload });
      } else {
        await lostMutation.mutateAsync({ id: selectedAsset.id, payload });
      }
      setCloseAction(null);
      setSelectedAsset(null);
    } catch (error) {
      setCloseError(localizeApiError(error.message, t) || error.message);
    }
  };

  if (assetsQuery.isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-primary" />
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 px-page py-8">
      <PageHeader
        title={t("assets.title", { defaultValue: "Assets" })}
        description={t("assets.subtitle", { defaultValue: "Track manually created or expense-linked assets and close their lifecycle when they are sold, gifted, disposed, or lost." })}
      >
        <Button
          onClick={() => {
            resetCreate();
            setCreateOpen(true);
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t("assets.addButton", { defaultValue: "Add Asset" })}
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryStat title="Visible assets" value={assets.length} hint={`Filtered total: ${assetsResponse.total || 0}`} />
        <SummaryStat title="Owned now" value={summary.ownedCount} hint="Open lifecycle assets in this view" />
        <SummaryStat
          title="Visible purchase value"
          value={<CurrencyAmount value={summary.purchaseTotal} format="display" />}
          hint="Sum of filtered purchase values"
        />
        <SummaryStat
          title="Visible current value"
          value={<CurrencyAmount value={summary.currentTotal} format="display" />}
          hint={`Closed in view: ${summary.closedCount}`}
        />
      </div>

      <Card className="shadow-sm">
        <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_220px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search assets by title or description"
              className="rounded-2xl pl-9"
            />
          </div>
          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="rounded-2xl">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {assetsQuery.error ? (
        <Card className="border-red-500/20">
          <CardContent className="flex items-start gap-3 p-5 text-red-500">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{localizeApiError(assetsQuery.error.message, t) || assetsQuery.error.message}</p>
          </CardContent>
        </Card>
      ) : null}

      {assets.length === 0 ? (
        <EmptyState
          icon={Wallet}
          title="No assets yet"
          description="Create your first asset here and use this page to test the manual asset lifecycle flow."
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {assets.map((asset) => {
            const isClosed = asset.status !== "owned";
            return (
              <Card key={asset.id} className="shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <CardTitle className="truncate text-xl">{asset.title}</CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                        {asset.description || "No description"}
                      </p>
                    </div>
                    <Badge className={cn("border capitalize", statusTone(asset.status))}>
                      {asset.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-border bg-muted/20 p-3">
                      <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">Purchase value</p>
                      <CurrencyAmount value={asset.purchase_value} format="display" className="mt-2" />
                    </div>
                    <div className="rounded-2xl border border-border bg-muted/20 p-3">
                      <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">Current value</p>
                      <CurrencyAmount value={asset.current_value} format="display" className="mt-2" />
                    </div>
                  </div>

                  <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
                    <p>Origin expense: {asset.origin_event_id ?? "Not linked"}</p>
                    <p>Created: {formatDisplayDate(asset.created_at?.slice?.(0, 10), appLang)}</p>
                    <p>Updated: {formatDisplayDate(asset.updated_at?.slice?.(0, 10), appLang)}</p>
                    <p>Sold/closed: {asset.sold_date ? formatDisplayDate(asset.sold_date, appLang) : "Not closed"}</p>
                    {asset.sale_value != null ? (
                      <p className="sm:col-span-2">
                        Sale value: <CurrencyAmount value={asset.sale_value} format="display" />
                      </p>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" className="rounded-2xl" onClick={() => openEdit(asset)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                    <Button
                      className="rounded-2xl"
                      onClick={() => openSell(asset)}
                      disabled={isClosed}
                    >
                      Sell
                    </Button>
                    {CLOSE_ACTIONS.map((action) => (
                      <Button
                        key={action.key}
                        variant="outline"
                        className="rounded-2xl"
                        onClick={() => openClose(asset, action.key)}
                        disabled={isClosed}
                      >
                        <action.icon className="mr-2 h-4 w-4" />
                        {action.label}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </p>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="rounded-2xl" onClick={() => setPage((prev) => Math.max(1, prev - 1))} disabled={page <= 1}>
            Prev
          </Button>
          <Button variant="outline" className="rounded-2xl" onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))} disabled={page >= totalPages}>
            Next
          </Button>
        </div>
      </div>

      <AssetFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Create asset"
        submitLabel="Create asset"
        form={createForm}
        setForm={setCreateForm}
        onSubmit={handleCreate}
        isPending={createMutation.isPending}
        error={createError}
      />

      <AssetFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        title="Edit asset"
        submitLabel="Save changes"
        form={editForm}
        setForm={setEditForm}
        onSubmit={handleUpdate}
        isPending={updateMutation.isPending}
        error={editError}
        showStatus
      />

      <AssetSellDialog
        open={sellOpen}
        onOpenChange={setSellOpen}
        form={sellForm}
        setForm={setSellForm}
        wallets={wallets}
        onSubmit={handleSell}
        isPending={sellMutation.isPending}
        error={sellError}
      />

      <AssetCloseDialog
        open={!!closeAction}
        onOpenChange={(open) => {
          if (!open) setCloseAction(null);
        }}
        title={
          closeAction === "gift"
            ? "Gift asset"
            : closeAction === "dispose"
              ? "Dispose asset"
              : "Mark asset as lost"
        }
        form={closeForm}
        setForm={setCloseForm}
        onSubmit={handleCloseAction}
        isPending={giftMutation.isPending || disposeMutation.isPending || lostMutation.isPending}
        error={closeError}
      />
    </div>
  );
}
