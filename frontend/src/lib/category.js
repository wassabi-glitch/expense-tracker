import { Car, Gamepad2, Home, Utensils, Wrench, Circle } from "lucide-react";

export const CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Entertainment",
    "Utilities",
    "Other",
];

export const categoryIconMap = {
    Food: Utensils,
    Transport: Car,
    Housing: Home,
    Entertainment: Gamepad2,
    Utilities: Wrench,
    Other: Circle,
};

export const getCategoryBgClass = (category) => {
    switch (category) {
        case "Food":
            return `bg-green-100 hover:bg-green-200 border border-green-200 dark:bg-green-500/30 dark:hover:bg-green-500/15 dark:border-green-400/35`;
        case "Transport":
            return (
                "bg-blue-100 hover:bg-blue-200 border border-blue-200 " +
                "dark:bg-blue-500/30 dark:hover:bg-blue-500/15 dark:border-blue-400/35"
            );
        case "Utilities":
            return (
                "bg-orange-100 hover:bg-orange-200 border border-orange-200 " +
                "dark:bg-orange-500/30 dark:hover:bg-orange-500/15 dark:border-orange-400/35"
            );
        case "Entertainment":
            return (
                "bg-violet-100 hover:bg-violet-200 border border-violet-200 " +
                "dark:bg-violet-500/30 dark:hover:bg-violet-500/15 dark:border-violet-400/35"
            );
        case "Housing":
            return (
                "bg-teal-100 hover:bg-teal-200 border border-teal-200 " +
                "dark:bg-teal-500/30 dark:hover:bg-teal-500/15 dark:border-teal-400/35"
            );
        case "Other":
            return (
                "bg-slate-100 hover:bg-slate-200 border border-slate-200 " +
                "dark:bg-slate-500/30 dark:hover:bg-slate-400/15 dark:border-slate-300/30"
            );
        default:
            return "";
    }
};
