import { InteractiveTooltip } from "@/components/InteractiveTooltip";
import {
  formatAmountDisplay,
  formatCompactUzs,
  formatUzs,
  isCompactAmountDisplayValue,
  isCompactUzsValue,
} from "@/lib/format";

const CURRENCY_LABEL_CLASS = "text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70";

function getFormattedAmount(value, format = "full") {
  if (format === "compact") return formatCompactUzs(value);
  if (format === "display") return formatAmountDisplay(value);
  return formatUzs(value);
}

function usesCompactAmount(value, format = "full") {
  if (format === "compact") return isCompactUzsValue(value);
  if (format === "display") return isCompactAmountDisplayValue(value);
  return false;
}

export function CurrencyAmount({
  value,
  prefix = "",
  format = "full",
  tooltip = "compact",
  side = "top",
  className = "",
  valueClassName = "",
  currencyClassName = "",
  contentClassName = "",
  includeCurrency = true,
  tooltipContent,
}) {
  const displayValue = getFormattedAmount(value, format);
  const fullValue = formatUzs(value);
  const shouldTooltip =
    tooltip === "always" || (tooltip === "compact" && usesCompactAmount(value, format));

  const content = tooltipContent ?? `${prefix}${fullValue} UZS`;
  const body = (
    <>
      <span className={valueClassName}>{prefix}{displayValue}</span>
      {includeCurrency ? <span className={`${CURRENCY_LABEL_CLASS} ${currencyClassName}`.trim()}>UZS</span> : null}
    </>
  );

  if (!shouldTooltip) {
    return <span className={className}>{body}</span>;
  }

  return (
    <InteractiveTooltip
      content={content}
      className={className}
      contentClassName={contentClassName}
      side={side}
    >
      {body}
    </InteractiveTooltip>
  );
}
