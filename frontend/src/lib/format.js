const UZ_MONTHS_SHORT = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"];
const RU_MONTHS_SHORT = ["Yanv", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek"];
const EN_MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const UZ_MONTHS_LONG = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"];
const RU_MONTHS_LONG = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
const EN_MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export const getAppLang = (i18n) => String(i18n?.resolvedLanguage || i18n?.language || "en").toLowerCase();

const normalizeAppLang = (appLang) => String(appLang || "en").toLowerCase();

export const getDateLocale = (appLang) => {
    const lang = normalizeAppLang(appLang);
    return lang.startsWith("uz") ? "uz-UZ" : lang.startsWith("ru") ? "ru-RU" : "en-US";
};

export const getFallbackMonthsShort = (appLang) => {
    const lang = normalizeAppLang(appLang);
    if (lang.startsWith("uz")) return UZ_MONTHS_SHORT;
    if (lang.startsWith("ru")) return RU_MONTHS_SHORT;
    return EN_MONTHS_SHORT;
};

export const getFallbackMonthsLong = (appLang) => {
    const lang = normalizeAppLang(appLang);
    if (lang.startsWith("uz")) return UZ_MONTHS_LONG;
    if (lang.startsWith("ru")) return RU_MONTHS_LONG;
    return EN_MONTHS_LONG;
};

export const formatUzs = (value) => {
    return String(Number(value || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
};

export const formatUzsCard = (value) => {
    const num = Number(value || 0);
    if (num >= 1_000_000_000_000) {
        return `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
    }
    return formatUzs(num);
};

export const formatCompactUzs = (value) => {
    const originalNum = Number(value || 0);
    const num = Math.abs(originalNum);
    const sign = originalNum < 0 ? "-" : "";
    
    let result;
    if (num >= 1_000_000_000_000) result = `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
    else if (num >= 1_000_000_000) result = `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
    else if (num >= 1_000_000) result = `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
    else if (num >= 1_000) result = `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
    else result = num;

    return `${sign}${result}`;
};

export const formatCompactUzsFromMillion = (value) => {
    const originalNum = Number(value || 0);
    const num = Math.abs(originalNum);
    const sign = originalNum < 0 ? "-" : "";

    let result;
    if (num >= 1_000_000_000_000) result = `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
    else if (num >= 1_000_000_000) result = `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
    else if (num >= 1_000_000) result = `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
    else result = formatUzs(num);

    return `${sign}${result}`;
};

export const formatAmountDisplay = (value) => {
    const originalNum = Number(value || 0);
    const num = Math.abs(originalNum);
    const sign = originalNum < 0 ? "-" : "";

    let result;
    if (num >= 1_000_000_000_000) result = `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
    else if (num >= 1_000_000_000) result = `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
    else result = formatUzs(num);

    return `${sign}${result}`;
};

export const isCompactUzsValue = (value) => Math.abs(Number(value || 0)) >= 1_000;
export const isCompactMobileAmountValue = (value) => Math.abs(Number(value || 0)) >= 1_000_000;

export const isCompactAmountDisplayValue = (value) => Math.abs(Number(value || 0)) >= 1_000_000_000;

export const parseAmountInput = (val) => {
    return Number(String(val || "").replace(/\s/g, ""));
};

export const formatAmountInput = (raw, maxDigits = 12) => {
    const digits = String(raw ?? "").replace(/\D/g, "").slice(0, maxDigits);
    if (!digits) return "";
    const normalized = digits.replace(/^0+(?=\d)/, "");
    return normalized.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
};

export const formatDisplayDate = (value, appLang) => {
    if (!value) return "-";
    const [y, m, d] = String(value).split("-").map(Number);
    if (!y || !m || !d) return value;

    const dateLocale = getDateLocale(appLang);
    const formatted = new Intl.DateTimeFormat(dateLocale, {
        year: "numeric",
        month: "short",
        day: "numeric",
    }).format(new Date(Date.UTC(y, m - 1, d)));

    if (/M\d{2}/.test(formatted)) {
        const fallbackMonths = getFallbackMonthsShort(appLang);
        return `${fallbackMonths[m - 1]} ${d}, ${y}`;
    }
    return formatted;
};

/**
 * Formats an absolute timestamp (UTC ISO string) into the user's local time.
 * e.g. "April 29, 10:44 PM" or "29 Apr, 2026 22:44"
 */
export const formatDisplayDateTime = (isoString, appLang) => {
    if (!isoString) return "-";
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    const lang = normalizeAppLang(appLang);
    const dateLocale = getDateLocale(appLang);
    
    // We use a natural layout: Month Day, Year, HH:MM
    const options = {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: lang.startsWith("en"), // Use 12h for English, 24h for RU/UZ
    };

    const formatted = new Intl.DateTimeFormat(dateLocale, options).format(date);

    // Handle Intl fallbacks for older environments or specific locales (e.g. M04)
    if (/M\d{2}/.test(formatted)) {
        const fallbackMonths = getFallbackMonthsShort(appLang);
        const y = date.getFullYear();
        const m = date.getMonth();
        const d = date.getDate();
        const hh = String(date.getHours()).padStart(2, "0");
        const mm = String(date.getMinutes()).padStart(2, "0");
        
        if (appLang.startsWith("en")) {
            const h12 = date.getHours() % 12 || 12;
            const ampm = date.getHours() >= 12 ? "PM" : "AM";
            return `${fallbackMonths[m]} ${d}, ${y} ${h12}:${mm} ${ampm}`;
        }
        return `${d} ${fallbackMonths[m]}, ${y} ${hh}:${mm}`;
    }
    
    return formatted;
};

export const formatPrettyDate = (isoDate, appLang) => {
    if (!isoDate) return "";
    const date = new Date(isoDate);
    if (appLang?.startsWith("uz")) {
        const d = date.getDate();
        const month = UZ_MONTHS_SHORT[date.getMonth()] || "";
        return `${d} ${month}`;
    }
    const dateLocale = getDateLocale(appLang);
    return date.toLocaleDateString(dateLocale, { month: "short", day: "numeric" });
};

export const shortMMDD = (iso) => String(iso || "").slice(5);

export const formatMonthYear = (yearOrValue, monthFallback, appLangFallback) => {
    let y, m, appLang;
    if (typeof yearOrValue === "string" && yearOrValue.includes("-")) {
        [y, m] = String(yearOrValue).split("-").map(Number);
        appLang = monthFallback || "en";
    } else {
        y = yearOrValue;
        m = monthFallback;
        appLang = appLangFallback || "en";
    }

    if (!y || !m) return "";
    // For Uzbek/Russian, prefer explicit month lists to avoid English fallbacks across platforms.
    if (appLang.startsWith("uz") || appLang.startsWith("ru")) {
        const fallbackMonths = getFallbackMonthsLong(appLang);
        return `${fallbackMonths[m - 1]} ${y}`;
    }

    const dateLocale = getDateLocale(appLang);
    const formatted = new Intl.DateTimeFormat(dateLocale, { month: "long", year: "numeric" }).format(
        new Date(Date.UTC(y, m - 1, 1))
    );
    if (/M\d{2}/.test(formatted)) {
        const fallbackMonths = getFallbackMonthsLong(appLang);
        return `${fallbackMonths[m - 1]} ${y}`;
    }
    return formatted;
};

export const formatRelativeTime = (isoDate) => {
    if (!isoDate) return "";
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;

    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};
