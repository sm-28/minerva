export const PLANS = {
  trial: {
    name: "Trial",
    maxBusinesses: 1,
    maxDocumentStorageMB: 100,
    maxTextChats: 10,
    maxSpeechChats: 10,
  },
  pro: {
    name: "Pro",
    maxBusinesses: Infinity,
    maxDocumentStorageMB: 10240, // 10 GB
    maxTextChats: Infinity, // credits-based
    maxSpeechChats: Infinity, // credits-based
  },
} as const;

export type PlanType = keyof typeof PLANS;

export function getPlanLimits(plan: PlanType) {
  return PLANS[plan] || PLANS.trial;
}

export function formatStorageSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export function isTrialPlan(plan: string): boolean {
  return plan === "trial";
}
