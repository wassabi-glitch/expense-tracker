import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  createAsset,
  updateAsset,
  sellAsset,
  giftAsset,
  disposeAsset,
  markAssetLost,
} from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { localizeApiError } from "@/lib/errorMessages";

async function invalidateAssetQueries(queryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["assets"] }),
    queryClient.invalidateQueries({ queryKey: ["wallets"] }),
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
    queryClient.invalidateQueries({ queryKey: ["expenses"] }),
    queryClient.invalidateQueries({ queryKey: ["income"] }),
  ]);
}

export function useAssetMutations() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { t } = useTranslation();

  const createMutation = useMutation({
    mutationFn: createAsset,
    onSuccess: async (data) => {
      await invalidateAssetQueries(queryClient);
      toast.success(
        t("assets.toastCreated", { defaultValue: "Asset created" }),
        data?.title || t("assets.title", { defaultValue: "Assets" })
      );
    },
    onError: (error) => {
      toast.error(
        t("assets.toastCreateFailed", { defaultValue: "Failed to create asset" }),
        localizeApiError(error.message, t) || error.message
      );
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateAsset(id, payload),
    onSuccess: async (data) => {
      await invalidateAssetQueries(queryClient);
      toast.success(
        t("assets.toastUpdated", { defaultValue: "Asset updated" }),
        data?.title || t("assets.title", { defaultValue: "Assets" })
      );
    },
    onError: (error) => {
      toast.error(
        t("assets.toastUpdateFailed", { defaultValue: "Failed to update asset" }),
        localizeApiError(error.message, t) || error.message
      );
    },
  });

  const sellMutation = useMutation({
    mutationFn: ({ id, payload }) => sellAsset(id, payload),
    onSuccess: async (data) => {
      await invalidateAssetQueries(queryClient);
      toast.success(
        t("assets.toastSold", { defaultValue: "Asset sold" }),
        data?.title || t("assets.title", { defaultValue: "Assets" })
      );
    },
    onError: (error) => {
      toast.error(
        t("assets.toastSellFailed", { defaultValue: "Failed to sell asset" }),
        localizeApiError(error.message, t) || error.message
      );
    },
  });

  const giftMutation = useMutation({
    mutationFn: ({ id, payload }) => giftAsset(id, payload),
    onSuccess: async (data) => {
      await invalidateAssetQueries(queryClient);
      toast.success(
        t("assets.toastGifted", { defaultValue: "Asset gifted" }),
        data?.title || t("assets.title", { defaultValue: "Assets" })
      );
    },
    onError: (error) => {
      toast.error(
        t("assets.toastGiftFailed", { defaultValue: "Failed to gift asset" }),
        localizeApiError(error.message, t) || error.message
      );
    },
  });

  const disposeMutation = useMutation({
    mutationFn: ({ id, payload }) => disposeAsset(id, payload),
    onSuccess: async (data) => {
      await invalidateAssetQueries(queryClient);
      toast.success(
        t("assets.toastDisposed", { defaultValue: "Asset disposed" }),
        data?.title || t("assets.title", { defaultValue: "Assets" })
      );
    },
    onError: (error) => {
      toast.error(
        t("assets.toastDisposeFailed", { defaultValue: "Failed to dispose asset" }),
        localizeApiError(error.message, t) || error.message
      );
    },
  });

  const lostMutation = useMutation({
    mutationFn: ({ id, payload }) => markAssetLost(id, payload),
    onSuccess: async (data) => {
      await invalidateAssetQueries(queryClient);
      toast.success(
        t("assets.toastLost", { defaultValue: "Asset marked as lost" }),
        data?.title || t("assets.title", { defaultValue: "Assets" })
      );
    },
    onError: (error) => {
      toast.error(
        t("assets.toastLostFailed", { defaultValue: "Failed to mark asset as lost" }),
        localizeApiError(error.message, t) || error.message
      );
    },
  });

  return {
    createMutation,
    updateMutation,
    sellMutation,
    giftMutation,
    disposeMutation,
    lostMutation,
  };
}
