import { rawApiClient } from "./client";

export async function getHealth() {
    const response = await rawApiClient.get("/health", { skipAuthRefresh: true });
    return response.data;
}
