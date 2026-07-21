import { useMutation } from "@tanstack/react-query";
import { analyze } from "@/lib/api";
import { useTerminalStore } from "@/store/terminal-store";

let activeController: AbortController | undefined;
export function useAnalysis() {
  const store = useTerminalStore();
  return useMutation({
    mutationFn: async () => {
      activeController?.abort();
      activeController = new AbortController();
      const requestId = crypto.randomUUID();
      store.beginAnalysis(requestId);
      try {
        const payload = await analyze(
          store.symbol,
          store.timeframe,
          store.model,
          activeController.signal,
        );
        if (!payload.decision)
          throw new Error(
            payload.error || "The backend returned no normalized decision.",
          );
        store.acceptDecision(requestId, payload.decision);
        return payload;
      } catch (error) {
        if ((error as Error).name !== "AbortError")
          store.failAnalysis(requestId);
        throw error;
      }
    },
  });
}
