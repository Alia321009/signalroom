import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch, apiPost, apiPut } from "../lib/api";
import { isAuthenticated } from "../lib/auth";
import type { BotSettings, Call, Member, PublicCall } from "../lib/types";

const FALLBACK_POLL_MS = 20000;

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<Member>("/members/me"),
    enabled: isAuthenticated(),
  });
}

export function useCalls(limit: number = 100) {
  return useQuery({
    queryKey: ["calls", limit],
    queryFn: () => apiGet<Call[]>(`/calls?limit=${limit}`),
    enabled: isAuthenticated(),
    refetchInterval: FALLBACK_POLL_MS,
  });
}

export function usePublicTrackRecord() {
  return useQuery({
    queryKey: ["public-calls"],
    queryFn: () => apiGet<PublicCall[]>("/calls/public"),
  });
}

export function useCreateCall() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      symbol: string; direction: "buy" | "sell"; entry: number; sl: number;
      tp1: number; tp2?: number | null; tp3?: number | null; valid_until: string; notes?: string | null;
    }) => apiPost<Call>("/calls", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["calls"] }),
  });
}

export function useUpdateCall() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; status?: string; outcome_r?: number; notes?: string }) =>
      apiPatch<Call>(`/calls/${id}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["calls"] }),
  });
}

export function useMembers() {
  return useQuery({
    queryKey: ["members"],
    queryFn: () => apiGet<Member[]>("/members"),
    enabled: isAuthenticated(),
  });
}

export function useUpdateSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memberId, ...body }: { memberId: number; tier?: string; status?: string; broker?: string; paid_until?: string }) =>
      apiPatch<Member>(`/members/${memberId}/subscription`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["members"] }),
  });
}

export function useSetBroker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (broker: "exness" | "xm") => apiPost(`/members/me/broker?broker=${broker}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useBotSettings() {
  return useQuery({
    queryKey: ["bot-settings"],
    queryFn: () => apiGet<BotSettings>("/bot-settings/me"),
    enabled: isAuthenticated(),
  });
}

export function useUpdateBotSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<BotSettings, "enabled" | "risk_pct" | "max_daily_loss_pct" | "symbols">>) =>
      apiPut<BotSettings>("/bot-settings/me", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bot-settings"] }),
  });
}

export function useRotateApiKey() {
  return useMutation({
    mutationFn: () => apiPost<{ api_key: string }>("/bot-settings/me/rotate-key"),
  });
}
