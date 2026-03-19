import { formatUzs } from "@/lib/format";

export const formatMoneyBold = (text) => {
    if (!text) return text;

    // Single capture group: match "number + optional space + currency label" as one unit.
    // This avoids the two-group split bug where the currency string was fed into formatUzs → "0".
    const regex = /(\d[\d, ]*\s*(?:UZS|so'm|so‘m))/gi;
    const parts = text.split(regex);

    return parts.map((part, i) => {
        if (i % 2 === 1) {
            // part = "50 000 UZS" or "50000 UZS" – strip the label and format the number
            const currencyMatch = part.match(/^([\d ,]+)\s*(UZS|so'm|so‘m)$/i);
            if (!currencyMatch) return part;
            const num = Number(currencyMatch[1].replace(/[\s,]/g, ""));
            const formatted = formatUzs(num);
            return (
                <strong key={i} className="inline-flex items-baseline gap-0.5 font-bold text-foreground">
                    {formatted}
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                        {currencyMatch[2]}
                    </span>
                </strong>
            );
        }
        return part;
    });
};
