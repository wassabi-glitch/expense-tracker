const UZ_MONTHS_SHORT = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"];
const RU_MONTHS_SHORT = ["Yanv", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek"];
const EN_MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const UZ_MONTHS_LONG = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"];
const RU_MONTHS_LONG = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
const EN_MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export const getAppLang = (i18n) => String(i18n?.resolvedLanguage || i18n?.language || "en").toLowerCase();

export const getDateLocale = (appLang) =>
    appLang.startsWith("uz") ? "uz-UZ" : appLang.startsWith("ru") ? "ru-RU" : "en-US";

export const getFallbackMonthsShort = (appLang) => {
    if (appLang.startsWith("uz")) return UZ_MONTHS_SHORT;
    if (appLang.startsWith("ru")) return RU_MONTHS_SHORT;
    return EN_MONTHS_SHORT;
};

export const getFallbackMonthsLong = (appLang) => {
    if (appLang.startsWith("uz")) return UZ_MONTHS_LONG;
    if (appLang.startsWith("ru")) return RU_MONTHS_LONG;
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
    const num = Math.abs(Number(value || 0));
    if (num >= 1_000_000_000_000) return `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
    if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
    return num;
};

export const formatAmountDisplay = (value) => {
    const num = Math.abs(Number(value || 0));
    if (num >= 1_000_000_000_000) return `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
    if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
    return formatUzs(num);
};

export const isCompactUzsValue = (value) => Math.abs(Number(value || 0)) >= 1_000;

export const isCompactAmountDisplayValue = (value) => Math.abs(Number(value || 0)) >= 1_000_000_000;

export const formatAmountInput = (raw, maxDigits = 15) => {
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
