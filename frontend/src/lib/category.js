import {
    ShoppingCart,
    Utensils,
    Home,
    Wrench,
    CalendarClock,
    Car,
    HeartPulse,
    Smartphone,
    Sparkles,
    GraduationCap,
    Shirt,
    Users,
    Gamepad2,
    HandHeart,
    CreditCard,
    Briefcase,
    Landmark,
    Banknote,
    Plane,
    PawPrint,
    Circle
} from "lucide-react";

export const CATEGORIES = [
    "Groceries",
    "Dining Out",
    "Electronics",
    "Housing",
    "Utilities",
    "Subscriptions",
    "Transport",
    "Health",
    "Personal care",
    "Education",
    "Clothing",
    "Family & Events",
    "Entertainment",
    "Installments & Debt",
    "Business / Work",
    "Bank Fees & Interest",
    "Debt Charges",
    "Travel",
    "Charity",
    "Animals & Pets",
];

export const FINANCING_CONTEXT_CATEGORY = "Installments & Debt";

export const SPENDING_CATEGORIES = CATEGORIES.filter(
    (category) => category !== FINANCING_CONTEXT_CATEGORY
);

export const categoryIconMap = {
    Groceries: ShoppingCart,
    "Dining Out": Utensils,
    Electronics: Smartphone,
    Housing: Home,
    Utilities: Wrench,
    Subscriptions: CalendarClock,
    Transport: Car,
    Health: HeartPulse,
    "Personal care": Sparkles,
    Education: GraduationCap,
    Clothing: Shirt,
    "Family & Events": Users,
    Entertainment: Gamepad2,
    "Installments & Debt": CreditCard,
    "Business / Work": Briefcase,
    "Bank Fees & Interest": Banknote,
    "Debt Charges": Landmark,
    Travel: Plane,
    Charity: HandHeart,
    "Animals & Pets": PawPrint,
    Other: Circle,
};

export const getCategoryBgClass = (category) => {
    switch (category) {
        case "Groceries":
            return "bg-emerald-100 hover:bg-emerald-200 border border-emerald-200 dark:bg-emerald-500/30 dark:hover:bg-emerald-500/15 dark:border-emerald-400/35";
        case "Dining Out":
            return "bg-orange-100 hover:bg-orange-200 border border-orange-200 dark:bg-orange-500/30 dark:hover:bg-orange-500/15 dark:border-orange-400/35";
        case "Electronics":
            return "bg-cyan-100 hover:bg-cyan-200 border border-cyan-200 dark:bg-cyan-500/30 dark:hover:bg-cyan-500/15 dark:border-cyan-400/35";
        case "Housing":
            return "bg-blue-100 hover:bg-blue-200 border border-blue-200 dark:bg-blue-500/30 dark:hover:bg-blue-500/15 dark:border-blue-400/35";
        case "Utilities":
            return "bg-yellow-100 hover:bg-yellow-200 border border-yellow-200 dark:bg-yellow-500/30 dark:hover:bg-yellow-500/15 dark:border-yellow-400/35";
        case "Subscriptions":
            return "bg-purple-100 hover:bg-purple-200 border border-purple-200 dark:bg-purple-500/30 dark:hover:bg-purple-500/15 dark:border-purple-400/35";
        case "Transport":
            return "bg-sky-100 hover:bg-sky-200 border border-sky-200 dark:bg-sky-500/30 dark:hover:bg-sky-500/15 dark:border-sky-400/35";
        case "Health":
            return "bg-red-100 hover:bg-red-200 border border-red-200 dark:bg-red-500/30 dark:hover:bg-red-500/15 dark:border-red-400/35";
        case "Personal care":
            return "bg-indigo-100 hover:bg-indigo-200 border border-indigo-200 dark:bg-indigo-500/30 dark:hover:bg-indigo-500/15 dark:border-indigo-400/35";
        case "Education":
            return "bg-amber-100 hover:bg-amber-200 border border-amber-200 dark:bg-amber-500/30 dark:hover:bg-amber-500/15 dark:border-amber-400/35";
        case "Clothing":
            return "bg-pink-100 hover:bg-pink-200 border border-pink-200 dark:bg-pink-500/30 dark:hover:bg-pink-500/15 dark:border-pink-400/35";
        case "Family & Events":
            return "bg-lime-100 hover:bg-lime-200 border border-lime-200 dark:bg-lime-500/30 dark:hover:bg-lime-500/15 dark:border-lime-400/35";
        case "Entertainment":
            return "bg-fuchsia-100 hover:bg-fuchsia-200 border border-fuchsia-200 dark:bg-fuchsia-500/30 dark:hover:bg-fuchsia-500/15 dark:border-fuchsia-400/35";
        case "Installments & Debt":
            return "bg-slate-100 hover:bg-slate-200 border border-slate-200 dark:bg-slate-500/30 dark:hover:bg-slate-500/15 dark:border-slate-400/35";
        case "Business / Work":
            return "bg-teal-100 hover:bg-teal-200 border border-teal-200 dark:bg-teal-500/30 dark:hover:bg-teal-500/15 dark:border-teal-400/35";
        case "Bank Fees & Interest":
            return "bg-zinc-100 hover:bg-zinc-200 border border-zinc-200 dark:bg-zinc-500/30 dark:hover:bg-zinc-500/15 dark:border-zinc-400/35";
        case "Debt Charges":
            return "bg-rose-100 hover:bg-rose-200 border border-rose-200 dark:bg-rose-500/30 dark:hover:bg-rose-500/15 dark:border-rose-400/35";
        case "Travel":
            return "bg-violet-100 hover:bg-violet-200 border border-violet-200 dark:bg-violet-500/30 dark:hover:bg-violet-500/15 dark:border-violet-400/35";
        case "Charity":
            return "bg-green-100 hover:bg-green-200 border border-green-200 dark:bg-green-500/30 dark:hover:bg-green-500/15 dark:border-green-400/35";
        case "Animals & Pets":
            return "bg-stone-100 hover:bg-stone-200 border border-stone-200 dark:bg-stone-500/30 dark:hover:bg-stone-500/15 dark:border-stone-400/35";
        default:
            return "bg-gray-100 hover:bg-gray-200 border border-gray-200 dark:bg-gray-500/30 dark:hover:bg-gray-500/15 dark:border-gray-400/35";
    }
};

export const getCategoryColorClass = (category) => {
    switch (category) {
        case "Groceries": return "text-emerald-500";
        case "Dining Out": return "text-orange-500";
        case "Electronics": return "text-cyan-500";
        case "Housing": return "text-blue-500";
        case "Utilities": return "text-yellow-500";
        case "Subscriptions": return "text-purple-500";
        case "Transport": return "text-sky-500";
        case "Health": return "text-red-500";
        case "Personal care": return "text-indigo-500";
        case "Education": return "text-amber-500";
        case "Clothing": return "text-pink-500";
        case "Family & Events": return "text-lime-500";
        case "Entertainment": return "text-fuchsia-500";
        case "Installments & Debt": return "text-slate-500";
        case "Business / Work": return "text-teal-500";
        case "Bank Fees & Interest": return "text-zinc-500";
        case "Debt Charges": return "text-rose-500";
        case "Travel": return "text-violet-500";
        case "Charity": return "text-green-500";
        case "Animals & Pets": return "text-stone-500";
        default: return "text-muted-foreground";
    }
};
