const fs = require('fs');
const path = require('path');
const file = path.join('c:', 'Users', 'me', 'Desktop', 'MyPROJECTS', 'ExpenseTracker', 'frontend', 'src', 'features', 'dashboard', 'Dashboard.jsx');
let content = fs.readFileSync(file, 'utf8');

content = content.replace(
    '<span className="font-semibold">{formatCompactUzs(item.total)}</span> /{" "}\n                          <span className="font-semibold">{formatCompactUzs(item.budget_limit)}</span> UZS',
    '<span className="truncate">\n                            <span className="font-semibold">{formatCompactUzs(item.total)}</span> /{" "}\n                            <span className="font-semibold">{formatCompactUzs(item.budget_limit)}</span>\n                          </span>\n                          <span className="text-[10px] font-medium uppercase opacity-70 shrink-0">UZS</span>'
);

content = content.replace(
    '"inline-block min-w-[140px] overflow-hidden text-ellipsis whitespace-nowrap text-right tabular-nums text-foreground"',
    '"flex items-baseline justify-end gap-1 min-w-[140px] overflow-hidden text-ellipsis whitespace-nowrap text-right tabular-nums text-foreground"'
);

content = content.replace(
    '{Number(e.amount) >= 1_000_000 ? formatCompactUzs(e.amount) : formatUzs(e.amount)} UZS',
    '<span>{Number(e.amount) >= 1_000_000 ? formatCompactUzs(e.amount) : formatUzs(e.amount)}</span>\n                    <span className="text-[10px] uppercase opacity-70">UZS</span>'
);

content = content.replace(
    '<div className="font-semibold text-sm text-foreground/90 shrink-0 whitespace-nowrap">',
    '<div className="flex items-baseline justify-end gap-1 font-semibold text-sm text-foreground/90 shrink-0 whitespace-nowrap">'
);

content = content.replace(
    '{formatUzs(value)} UZS\n                          </span>,\n                          t("dashboard.amount"),',
    '<span>{formatUzs(value)}</span>\n                            <span className="text-[10px] uppercase opacity-70">UZS</span>\n                          </span>,\n                          t("dashboard.amount"),'
);
content = content.replace(
    '{formatUzs(value)} UZS\n                            </span>,\n                            t("dashboard.total"),',
    '<span>{formatUzs(value)}</span>\n                              <span className="text-[10px] uppercase opacity-70">UZS</span>\n                            </span>,\n                            t("dashboard.total"),'
);

content = content.replace(
    '<span style={{ color: "hsl(var(--primary))", fontWeight: 600 }}>',
    '<span style={{ color: "hsl(var(--primary))", fontWeight: 600 }} className="flex items-baseline gap-1">'
);
content = content.replace(
    '<span style={{ color: "hsl(var(--primary))", fontWeight: 600 }}>',
    '<span style={{ color: "hsl(var(--primary))", fontWeight: 600 }} className="flex items-baseline gap-1">'
);

content = content.replace(
    '{formatAmountDisplay(e.amount)} <span className="text-xs font-normal text-muted-foreground">UZS</span>',
    '<span>{formatAmountDisplay(e.amount)}</span>\n                          <span className="text-[10px] uppercase opacity-70">UZS</span>'
);

content = content.replace(
    '<div className="font-semibold text-sm tabular-nums text-right shrink-0 whitespace-nowrap">',
    '<div className="flex items-baseline justify-end gap-1 font-semibold text-sm tabular-nums text-right shrink-0 whitespace-nowrap">'
);

fs.writeFileSync(file, content);
console.log('Done');
