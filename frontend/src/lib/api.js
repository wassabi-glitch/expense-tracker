export { setAccessToken, isLoggedIn, silentRefresh } from "./api/client";
export { apiClient } from "./api/client";

export {
    signin,
    signup,
    forgotPassword,
    resendVerification,
    verifyEmail,
    resetPassword,
    logout,
    getGoogleLoginUrl,
} from "./api/auth";

export { getHealth } from "./api/health";
export { getCurrentUser, togglePremium, upsertOnboardingProfile, updateBudgetRolloverPreference } from "./api/users";
export { getCategories } from "./api/meta";
export { getBudgets, createBudget, updateBudget, deleteBudget } from "./api/budgets";
export { getExpenses, deleteExpense, createExpense, updateExpense, exportExpensesCsv } from "./api/expenses";
export { getRecurringExpenses, createRecurringExpense, updateRecurringExpense, deleteRecurringExpense, patchRecurringActive } from "./api/recurring";
export { getThisMonthStats, getDashboardSummary, getDailyTrend, getAnalyticsHistory, getMonthToDateTrend, getCategoryBreakdown } from "./api/analytics";
export {
    getIncomeSources,
    createIncomeSource,
    updateIncomeSource,
    updateIncomeSourceActive,
    deleteIncomeSource,
    getIncomeEntries,
    createIncomeEntry,
    updateIncomeEntry,
    deleteIncomeEntry,
} from "./api/income";
export { getSavingsSummary, depositToSavings, withdrawFromSavings } from "./api/savings";
export { getGoals, createGoal, updateGoal, contributeToGoal, returnFromGoal, archiveGoal, restoreGoal, deleteGoal } from "./api/goals";
