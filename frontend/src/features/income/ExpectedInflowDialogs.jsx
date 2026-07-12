import { useEffect, useMemo, useState } from "react";
import {
  Check,
  ChevronsUpDown,
  CircleDollarSign,
  Landmark,
  PackageCheck,
  Plus,
  ReceiptText,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createIncomeSource } from "@/lib/api";
import { formatAmountInput, formatDisplayDate, parseAmountInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import { MAX_INCOME_AMOUNT } from "./incomeSchemas";
import {
  getAssetSaleOptions,
  getEarnedOptions,
  getReceivableOptions,
  getRefundOptions,
} from "./ExpectedInflowSourcePicker";


const SOURCE_KINDS = [
  { value: "EARNED", label: "Earned", icon: CircleDollarSign },
  { value: "RECEIVABLE", label: "Debt repayment", icon: Landmark },
  { value: "REFUND", label: "Refund", icon: ReceiptText },
  { value: "ASSET_SALE", label: "Asset sale", icon: PackageCheck },
];

const maxAmountDigits = String(MAX_INCOME_AMOUNT).length;

function nextMonthDate(value, minimum) {
  const parsed = new Date(`${value}T00:00:00Z`);
  parsed.setUTCMonth(parsed.getUTCMonth() + 1);
  const result = parsed.toISOString().slice(0, 10);
  return result < minimum ? minimum : result;
}

function activeSchedules(item) {
  return (item?.schedules || []).filter((schedule) => schedule.is_active);
}

function distributeAmount(total, schedules) {
  let unallocated = total;
  return schedules.map((schedule) => {
    const amount = Math.min(unallocated, Number(schedule.remaining_amount || 0));
    unallocated -= amount;
    return { schedule_id: String(schedule.id), amount: amount ? String(amount) : "" };
  }).filter((row) => parseAmountInput(row.amount) > 0);
}

export function ExpectedInflowEditorDialog({
  open,
  onOpenChange,
  item,
  monthValue,
  todayISO,
  sources,
  debts,
  expenses,
  assets,
  onSubmit,
  pending,
}) {
  const [kind, setKind] = useState("EARNED");
  const [sourceId, setSourceId] = useState("");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const financialLocked = Boolean(item && !item.is_pristine);

  // Ticket 2: Creatable source selection state
  const [sourcePopoverOpen, setSourcePopoverOpen] = useState(false);
  const [sourceSearch, setSourceSearch] = useState("");
  const [creatingSource, setCreatingSource] = useState(false);

  const options = useMemo(() => {
    if (kind === "EARNED") return getEarnedOptions(sources);
    if (kind === "RECEIVABLE") return getReceivableOptions(debts);
    if (kind === "REFUND") return getRefundOptions(expenses);
    return getAssetSaleOptions(assets);
  }, [assets, debts, expenses, kind, sources]);

  // Ticket 2: Filtered earned options based on search text
  const filteredEarnedOptions = useMemo(() => {
    if (kind !== "EARNED") return [];
    const search = sourceSearch.trim().toLowerCase();
    if (!search) return options;
    return options.filter(
      (opt) => opt.label.toLowerCase().includes(search),
    );
  }, [kind, options, sourceSearch]);

  // Ticket 2: True when the search text does not match any existing source
  const showCreateOption = kind === "EARNED" && sourceSearch.trim().length > 0
    && !filteredEarnedOptions.some(
      (opt) => opt.label.toLowerCase() === sourceSearch.trim().toLowerCase(),
    );

  useEffect(() => {
    if (!open) return;
    const [year, month] = String(monthValue).split("-").map(Number);
    const defaultDate = `${year}-${String(month).padStart(2, "0")}-15`;
    setKind(item?.kind || "EARNED");
    setSourceId(String(item?.source_id || item?.debt_id || item?.refund_event_id || item?.asset_id || ""));
    setTitle(item?.title || "");
    setAmount(item ? formatAmountInput(String(item.original_amount), maxAmountDigits) : "");
    setDueDate(item?.next_due_date || defaultDate);
    setNote(item?.note || "");
    setError("");
    setSourceSearch("");
  }, [item, monthValue, open]);

  useEffect(() => {
    if (!open || item) return;
    setSourceId(options[0]?.id ? String(options[0].id) : "");
  }, [item, kind, open, options]);

  // Ticket 2: Inline income source creation
  const handleCreateSource = async () => {
    const name = sourceSearch.trim();
    if (!name || creatingSource) return;
    setCreatingSource(true);
    setError("");
    try {
      const created = await createIncomeSource({ name });
      // Select the newly created source
      setSourceId(String(created.id));
      setSourceSearch("");
      setSourcePopoverOpen(false);
    } catch (createError) {
      const detail =
        createError?.response?.data?.detail ||
        createError?.message ||
        "Could not create income source.";
      setError(typeof detail === "string" ? detail : "Could not create income source.");
      // Leave the draft intact — user can still pick an existing source.
    } finally {
      setCreatingSource(false);
    }
  };

  const optionLabel = (option) => option.label;
  const selectedLabel = options.find((opt) => String(opt.id) === sourceId)?.label || "";

  const submit = async () => {
    const amountValue = parseAmountInput(amount);
    if (!title.trim() || (!item && !sourceId) || (!financialLocked && (amountValue <= 0 || !dueDate))) {
      setError("Enter a title, source, positive amount, and expected date.");
      return;
    }
    const payload = { title: title.trim() };
    if (!financialLocked) {
      payload.amount = amountValue;
      payload.due_date = dueDate;
      payload.note = note.trim() || null;
    }
    if (!item) {
      payload.kind = kind;
      if (kind === "EARNED") payload.source_id = Number(sourceId);
      if (kind === "RECEIVABLE") payload.debt_id = Number(sourceId);
      if (kind === "REFUND") payload.refund_event_id = Number(sourceId);
      if (kind === "ASSET_SALE") payload.asset_id = Number(sourceId);
    }
    try {
      await onSubmit(payload);
      onOpenChange(false);
    } catch (requestError) {
      setError(requestError?.message || "Expected inflow could not be saved.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{item ? "Edit expected inflow" : "Add expected inflow"}</DialogTitle>
          <DialogDescription>{item?.source_label || "Choose the source of the expected wallet value."}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {!item ? (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {SOURCE_KINDS.map((option) => {
                const Icon = option.icon;
                return (
                  <button key={option.value} type="button" onClick={() => setKind(option.value)} className={cn("flex min-h-20 flex-col items-center justify-center gap-2 rounded-lg border px-2 py-3 text-sm font-medium", kind === option.value ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:bg-muted")}>
                    <Icon className="h-5 w-5" />{option.label}
                  </button>
                );
              })}
            </div>
          ) : null}
          {!item ? (
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Source</label>
              {kind === "EARNED" ? (
                /* Ticket 2: Creatable combobox for earned income sources */
                <Popover open={sourcePopoverOpen} onOpenChange={setSourcePopoverOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={sourcePopoverOpen}
                      className="w-full justify-between"
                    >
                      {selectedLabel || "Select income source"}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                    <Command>
                      <CommandInput
                        placeholder="Search or create a source..."
                        value={sourceSearch}
                        onValueChange={setSourceSearch}
                      />
                      <CommandList>
                        <CommandEmpty>
                          {showCreateOption ? (
                            <Button
                              variant="ghost"
                              className="w-full justify-start font-normal text-sm"
                              disabled={creatingSource}
                              onClick={handleCreateSource}
                            >
                              <Plus className="mr-2 h-4 w-4" />
                              {creatingSource
                                ? "Creating..."
                                : `Create "${sourceSearch.trim()}"`}
                            </Button>
                          ) : (
                            "No income source found."
                          )}
                        </CommandEmpty>
                        <CommandGroup>
                          {filteredEarnedOptions.map((option) => (
                            <CommandItem
                              key={option.id}
                              value={option.label}
                              onSelect={() => {
                                setSourceId(String(option.id));
                                setSourceSearch("");
                                setSourcePopoverOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  sourceId === String(option.id) ? "opacity-100" : "opacity-0",
                                )}
                              />
                              {option.label}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              ) : (
                /* Non-earned kinds: plain select (debts, refunds, assets) */
                <Select value={sourceId || undefined} onValueChange={setSourceId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    {options.map((option) => (
                      <SelectItem key={option.id} value={String(option.id)}>
                        {optionLabel(option)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          ) : null}
          <div className="space-y-1.5"><label className="text-sm font-medium">Title</label><Input value={title} maxLength={100} onChange={(event) => setTitle(event.target.value)} /></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5"><label className="text-sm font-medium">Expected amount</label><Input disabled={financialLocked} inputMode="numeric" value={amount} onChange={(event) => setAmount(formatAmountInput(event.target.value, maxAmountDigits))} /></div>
            <div className="space-y-1.5"><label className="text-sm font-medium">Expected date</label><Input disabled={financialLocked} type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />{!financialLocked && dueDate && dueDate < todayISO ? <p className="text-xs text-amber-600">Overdue on creation</p> : null}</div>
          </div>
          <div className="space-y-1.5"><label className="text-sm font-medium">Note</label><Input disabled={financialLocked} value={note} maxLength={200} onChange={(event) => setNote(event.target.value)} /></div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button><Button onClick={submit} disabled={pending}>Save</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ReceiveExpectedInflowDialog({ item, open, onOpenChange, wallets, todayISO, onSubmit, pending, targetSchedule }) {
  const schedules = useMemo(() => activeSchedules(item), [item]);
  const [actualAmount, setActualAmount] = useState("");
  const [receivedDate, setReceivedDate] = useState(todayISO);
  const [walletRows, setWalletRows] = useState([]);
  const [scheduleRows, setScheduleRows] = useState([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !item) return;
    // If a specific schedule was targeted, pre-fill its remaining amount
    const targetId = targetSchedule?.id;
    const targetRemaining = targetId ? Number(targetSchedule.remaining_amount || 0) : Number(item.outstanding_amount || 0);
    const amount = Math.min(targetRemaining, Number(item.outstanding_amount || 0));
    setActualAmount(formatAmountInput(String(amount), maxAmountDigits));
    setReceivedDate(todayISO);
    setWalletRows(wallets[0] ? [{ wallet_id: String(wallets[0].id), amount: String(amount) }] : []);
    // If targeting a specific schedule, pre-select that schedule
    if (targetId) {
      setScheduleRows([{ schedule_id: String(targetId), amount: String(amount) }]);
    } else {
      setScheduleRows(distributeAmount(amount, schedules));
    }
    setNote("");
    setError("");
  }, [item, open, schedules, todayISO, wallets, targetSchedule]);

  if (!item) return null;
  const actual = parseAmountInput(actualAmount);
  const expectedAllocationTotal = Math.min(actual, Number(item.outstanding_amount || 0));
  const walletTotal = walletRows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0);
  const scheduleTotal = schedules.length > 1
    ? scheduleRows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0)
    : expectedAllocationTotal;
  const updateRow = (setter, index, field, value) => setter((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [field]: value } : row));
  const changeActual = (value) => {
    const formatted = formatAmountInput(value, maxAmountDigits);
    const parsed = parseAmountInput(formatted);
    setActualAmount(formatted);
    if (walletRows.length === 1) setWalletRows((rows) => [{ ...rows[0], amount: formatted }]);
    setScheduleRows(distributeAmount(parsed, schedules));
  };
  const submit = async () => {
    if (actual <= 0 || walletTotal !== actual || scheduleTotal !== expectedAllocationTotal || !receivedDate) {
      setError("Wallets must equal the actual receipt, and schedules must equal the expected amount being satisfied.");
      return;
    }
    const payload = {
      actual_amount: actual,
      received_date: receivedDate,
      wallet_allocations: walletRows.map((row) => ({ wallet_id: Number(row.wallet_id), amount: parseAmountInput(row.amount) })),
      note: note.trim() || null,
      idempotency_key: globalThis.crypto?.randomUUID?.() || `receive-${item.id}-${Date.now()}`,
    };
    if (schedules.length > 1) {
      payload.schedule_allocations = scheduleRows.map((row) => ({ schedule_id: Number(row.schedule_id), amount: parseAmountInput(row.amount) }));
    }
    try {
      await onSubmit(payload);
      onOpenChange(false);
    } catch (requestError) {
      setError(requestError?.message || "Receipt could not be recorded.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle>Receive expected inflow</DialogTitle><DialogDescription>{item.title}</DialogDescription></DialogHeader>
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2"><div className="space-y-1.5"><label className="text-sm font-medium">Actual amount</label><Input inputMode="numeric" value={actualAmount} onChange={(event) => changeActual(event.target.value)} /></div><div className="space-y-1.5"><label className="text-sm font-medium">Received date</label><Input type="date" max={todayISO} value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} /></div></div>
          <div className="space-y-2"><div className="flex items-center justify-between"><p className="text-sm font-semibold">Destination wallets</p><Button type="button" size="sm" variant="outline" onClick={() => setWalletRows((rows) => [...rows, { wallet_id: "", amount: "" }])}><Plus className="mr-2 h-4 w-4" />Wallet</Button></div>{walletRows.map((row, index) => <div key={`${index}-${row.wallet_id}`} className="grid grid-cols-[minmax(0,1fr)_minmax(8rem,0.7fr)_auto] gap-2"><Select value={row.wallet_id || undefined} onValueChange={(value) => updateRow(setWalletRows, index, "wallet_id", value)}><SelectTrigger><SelectValue placeholder="Wallet" /></SelectTrigger><SelectContent>{wallets.map((wallet) => <SelectItem key={wallet.id} value={String(wallet.id)}>{wallet.name}</SelectItem>)}</SelectContent></Select><Input inputMode="numeric" value={row.amount} onChange={(event) => updateRow(setWalletRows, index, "amount", formatAmountInput(event.target.value, maxAmountDigits))} /><Button type="button" size="icon" variant="ghost" disabled={walletRows.length === 1} onClick={() => setWalletRows((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}><Trash2 className="h-4 w-4" /></Button></div>)}</div>
          {schedules.length > 1 ? <div className="space-y-2"><p className="text-sm font-semibold">Apply to schedules</p>{scheduleRows.map((row, index) => { const schedule = schedules.find((candidate) => candidate.id === Number(row.schedule_id)); return <div key={row.schedule_id} className="grid grid-cols-[minmax(0,1fr)_minmax(8rem,0.7fr)] gap-2"><div className="flex items-center rounded-md border px-3 text-sm">{formatDisplayDate(schedule?.due_date)} / {schedule?.remaining_amount} remaining</div><Input inputMode="numeric" value={row.amount} onChange={(event) => updateRow(setScheduleRows, index, "amount", formatAmountInput(event.target.value, maxAmountDigits))} /></div>; })}</div> : null}
          <Input value={note} maxLength={200} placeholder="Note" onChange={(event) => setNote(event.target.value)} />
          <div className="flex justify-between text-sm text-muted-foreground"><span>Wallets: {walletTotal}</span><span>Schedules: {scheduleTotal}</span></div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button><Button onClick={submit} disabled={pending}>Record receipt</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RescheduleExpectedInflowDialog({ item, open, onOpenChange, todayISO, onSubmit, pending, targetSchedule }) {
  const schedules = useMemo(() => activeSchedules(item), [item]);
  const [sourceScheduleId, setSourceScheduleId] = useState("");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const source = schedules.find((schedule) => String(schedule.id) === sourceScheduleId) || schedules[0];

  useEffect(() => {
    if (!open || !item || schedules.length === 0) return;
    // If a specific schedule was targeted, pre-select it as the source
    const targetId = targetSchedule?.id ? String(targetSchedule.id) : String(schedules[0].id);
    setSourceScheduleId(targetId);
    setError("");
  }, [item, open, schedules, targetSchedule]);
  useEffect(() => {
    if (!open || !source) return;
    setRows([{ amount: String(source.remaining_amount), due_date: nextMonthDate(source.due_date, todayISO), note: "" }]);
  }, [open, source, todayISO]);
  if (!item || !source) return null;
  const outstanding = Number(source.remaining_amount);
  const moveTotal = rows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0);
  const retainedAmount = Math.max(0, outstanding - moveTotal);
  const submit = async () => {
    if (moveTotal <= 0 || moveTotal > outstanding || rows.some((row) => !row.due_date || row.due_date < todayISO || parseAmountInput(row.amount) <= 0)) {
      setError("Enter a positive amount within this schedule and choose today or a future date.");
      return;
    }
    const allocations = rows.map((row) => ({ amount: parseAmountInput(row.amount), due_date: row.due_date, note: row.note || null }));
    if (retainedAmount > 0) allocations.unshift({ amount: retainedAmount, due_date: source.due_date, note: source.note || null });
    try {
      await onSubmit({ source_schedule_id: Number(source.id), allocations });
      onOpenChange(false);
    } catch (requestError) {
      setError(requestError?.message || "Schedule could not be changed.");
    }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle>Reschedule amount</DialogTitle><DialogDescription>{item.title}</DialogDescription></DialogHeader>
        <div className="space-y-3">
          {schedules.length > 1 ? <div className="space-y-1.5"><label className="text-sm font-medium">Schedule to change</label><Select value={String(source.id)} onValueChange={setSourceScheduleId}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{schedules.map((schedule) => <SelectItem key={schedule.id} value={String(schedule.id)}>{formatDisplayDate(schedule.due_date)} / {schedule.remaining_amount}</SelectItem>)}</SelectContent></Select></div> : null}
          {rows.map((row, index) => <div key={index} className="grid gap-2 sm:grid-cols-[minmax(8rem,0.8fr)_minmax(10rem,0.8fr)_minmax(0,1fr)_auto]"><Input inputMode="numeric" value={row.amount} onChange={(event) => setRows((items) => items.map((entry, rowIndex) => rowIndex === index ? { ...entry, amount: formatAmountInput(event.target.value, maxAmountDigits) } : entry))} /><Input type="date" min={todayISO} value={row.due_date} onChange={(event) => setRows((items) => items.map((entry, rowIndex) => rowIndex === index ? { ...entry, due_date: event.target.value } : entry))} /><Input placeholder="Note" value={row.note} onChange={(event) => setRows((items) => items.map((entry, rowIndex) => rowIndex === index ? { ...entry, note: event.target.value } : entry))} /><Button type="button" size="icon" variant="ghost" disabled={rows.length === 1} onClick={() => setRows((items) => items.filter((_, rowIndex) => rowIndex !== index))}><Trash2 className="h-4 w-4" /></Button></div>)}
          <div className="flex flex-wrap items-center justify-between gap-2"><Button type="button" size="sm" variant="outline" onClick={() => setRows((items) => [...items, { amount: "", due_date: nextMonthDate(items.at(-1)?.due_date || source.due_date, todayISO), note: "" }])}><Plus className="mr-2 h-4 w-4" />Another date</Button><div className="text-right text-sm"><p>Moving {moveTotal} of {outstanding}</p>{retainedAmount > 0 ? <p className="text-muted-foreground">{retainedAmount} stays on {formatDisplayDate(source.due_date)}</p> : null}</div></div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button><Button onClick={submit} disabled={pending}>Reschedule</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function WriteOffExpectedInflowDialog({ item, open, onOpenChange, todayISO, onSubmit, pending, targetSchedule }) {
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [writtenOffDate, setWrittenOffDate] = useState(todayISO);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!open || !item) return;
    // If a specific schedule was targeted, pre-fill its remaining amount
    const targetRemaining = targetSchedule?.id ? Number(targetSchedule.remaining_amount || 0) : Number(item.outstanding_amount || 0);
    const initialAmount = Math.min(targetRemaining, Number(item.outstanding_amount || 0));
    setAmount(formatAmountInput(String(initialAmount), maxAmountDigits));
    setReason("");
    setWrittenOffDate(todayISO);
    setError("");
  }, [item, open, todayISO, targetSchedule]);
  if (!item) return null;
  const submit = async () => {
    const value = parseAmountInput(amount);
    if (value <= 0 || value > Number(item.outstanding_amount) || !reason.trim()) {
      setError("Enter an amount within the outstanding balance and a reason.");
      return;
    }
    const payload = { amount: value, reason: reason.trim(), written_off_date: writtenOffDate };
    // Target specific schedule when launched from a ScheduleCard
    if (targetSchedule?.id) {
      payload.schedule_allocations = [{ schedule_id: targetSchedule.id, amount: value }];
    }
    try {
      await onSubmit(payload);
      onOpenChange(false);
    } catch (requestError) {
      setError(requestError?.message || "Amount could not be written off.");
    }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Write off expected amount</DialogTitle><DialogDescription>{item.title}</DialogDescription></DialogHeader>
        <div className="space-y-3"><div className="grid gap-3 sm:grid-cols-2"><div className="space-y-1.5"><label className="text-sm font-medium">Amount</label><Input inputMode="numeric" value={amount} onChange={(event) => setAmount(formatAmountInput(event.target.value, maxAmountDigits))} /></div><div className="space-y-1.5"><label className="text-sm font-medium">Date</label><Input type="date" max={todayISO} value={writtenOffDate} onChange={(event) => setWrittenOffDate(event.target.value)} /></div></div><div className="space-y-1.5"><label className="text-sm font-medium">Reason</label><Input value={reason} maxLength={200} onChange={(event) => setReason(event.target.value)} /></div>{error ? <p className="text-sm text-destructive">{error}</p> : null}</div>
        <DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button><Button onClick={submit} disabled={pending}>Write off</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
