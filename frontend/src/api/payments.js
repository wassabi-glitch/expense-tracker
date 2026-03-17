import { apiClient } from "@/lib/api";

export const createInvoice = async (planId) => {
    const response = await apiClient.post("/payments/create-invoice", { plan_id: planId });
    return response.data;
};
