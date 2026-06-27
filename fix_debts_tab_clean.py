with open('frontend/src/features/obligations/components/DebtsTab.jsx', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Import
c = c.replace(
    'import { DebtDetailsDialog } from "./DebtDetailsDialog";',
    'import { DebtDetailsDialog } from "./DebtDetailsDialog";\nimport { MIN_SUPPORTED_USER_DATE } from "../obligationSchemas";'
)

# 2. dateError
old_dateError = """  const dateError = () => {
    if (dueDate && date && dueDate < date) return "Expected date cannot be before the debt date.";
    return "";
  };"""
new_dateError = """  const dateError = () => {
    if (!date) return "Debt date is required.";
    if (date < MIN_SUPPORTED_USER_DATE) return "Date cannot be before 2020-01-01.";
    if (!dueDate) return "Due date is required.";
    if (dueDate < MIN_SUPPORTED_USER_DATE) return "Due date cannot be before 2020-01-01.";
    if (dueDate && date && dueDate < date) return "Expected date cannot be before the debt date.";
    return "";
  };"""
c = c.replace(old_dateError, new_dateError)

# 3. expected_return_date
c = c.replace(
    '      expected_return_date: dueDate || null,',
    '      expected_return_date: dueDate,'
)

# 4. Debt date Input
c = c.replace(
    '<Input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="h-11 rounded-md text-base" />',
    '<Input type="date" min={MIN_SUPPORTED_USER_DATE} value={date} onChange={(event) => setDate(event.target.value)} className="h-11 rounded-md text-base" />'
)

# 5. Due date Input
c = c.replace(
    '<Input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="h-11 rounded-md text-base" />\n                <p className="text-xs text-muted-foreground">Optional. Leave it blank if there is no clear date yet.</p>',
    '<Input type="date" min={date || MIN_SUPPORTED_USER_DATE} value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="h-11 rounded-md text-base" />\n                <p className="text-xs text-muted-foreground">Required. It keeps debt reports and reminders predictable.</p>'
)

# 6. SummaryTile Expected date
c = c.replace(
    '<SummaryTile icon={CalendarDays} label="Expected date" value={dueDate ? formatDisplayDate(dueDate, "en") : "No date yet"} helper={date ? `Debt date ${formatDisplayDate(date, "en")}` : "No debt date"} />',
    '<SummaryTile icon={CalendarDays} label="Expected date" value={formatDisplayDate(dueDate, "en")} helper={date ? `Debt date ${formatDisplayDate(date, "en")}` : "No debt date"} />'
)

# 7. SummaryTile Formal debts
c = c.replace(
    '<SummaryTile icon={ShieldCheck} label="Formal debts" value={formalCount} helper="Loans, installments, provider contracts" tone="info" />',
    '<SummaryTile icon={ShieldCheck} label="Formal debts" value={formalCount} helper="Loans, payment plans, provider contracts" tone="info" />'
)

# 8. Issue 3 changes (DebtRow)
c = c.replace(
    '''  const total = Number(debt.initial_amount || 0) + Number(debt.total_charges || 0);
  const paid = Math.max(total - Number(debt.remaining_amount || 0), 0);
  const progress = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;''',
    '''  const total = Number(debt.initial_amount || 0) + Number(debt.total_charges || 0);
  const paid = debt.total_paid || 0;
  const progress = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;'''
)

with open('frontend/src/features/obligations/components/DebtsTab.jsx', 'w', encoding='utf-8') as f:
    f.write(c)

print("Applied clean script")
