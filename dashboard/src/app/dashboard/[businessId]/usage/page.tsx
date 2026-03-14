import { auth } from "@/auth";
import { db } from "@/db";
import { businesses, documents } from "@/db/schema";
import { eq, sum } from "drizzle-orm";
import { redirect } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Crown,
  HardDrive,
  MessageSquare,
  Mic,
  Building2,
  Check,
  Sparkles,
} from "lucide-react";

export default async function UsagePage({
  params,
}: {
  params: Promise<{ businessId: string }>;
}) {
  const session = await auth();
  if (!session?.user?.id) redirect("/auth/signin");

  const { businessId } = await params;

  const [business] = await db
    .select()
    .from(businesses)
    .where(eq(businesses.id, businessId));

  if (!business) redirect("/");

  const [storageResult] = await db
    .select({ totalSize: sum(documents.size) })
    .from(documents)
    .where(eq(documents.businessId, businessId));

  const totalStorage = Number(storageResult?.totalSize || 0);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plan = ((session.user as any).plan as string) || "trial";
  const isTrialPlan = plan === "trial";

  const userBusinesses = await db
    .select()
    .from(businesses)
    .where(eq(businesses.ownerId, session.user.id));

  const usageItems = [
    {
      label: "Businesses",
      used: userBusinesses.length,
      limit: isTrialPlan ? 1 : "Unlimited",
      percentage: isTrialPlan ? (userBusinesses.length / 1) * 100 : 10,
      icon: Building2,
      color: "text-violet-500 dark:text-violet-400",
    },
    {
      label: "Document Storage",
      used: `${(totalStorage / (1024 * 1024)).toFixed(1)} MB`,
      limit: isTrialPlan ? "100 MB" : "10 GB",
      percentage: isTrialPlan
        ? (totalStorage / (100 * 1024 * 1024)) * 100
        : (totalStorage / (10 * 1024 * 1024 * 1024)) * 100,
      icon: HardDrive,
      color: "text-blue-500 dark:text-blue-400",
    },
    {
      label: "Text Chat Requests",
      used: "0",
      limit: isTrialPlan ? "10" : "Credits-based",
      percentage: 0,
      icon: MessageSquare,
      color: "text-emerald-500 dark:text-emerald-400",
    },
    {
      label: "Speech Chat Requests",
      used: "0",
      limit: isTrialPlan ? "10" : "Credits-based",
      percentage: 0,
      icon: Mic,
      color: "text-amber-500 dark:text-amber-400",
    },
  ];

  const trialFeatures = [
    "1 business",
    "100 MB document storage",
    "10 text chat requests",
    "10 speech chat requests",
  ];

  const proFeatures = [
    "Unlimited businesses",
    "10 GB document storage",
    "Credits-based text chats",
    "Credits-based speech chats",
    "Priority support",
    "Advanced analytics",
    "Custom integrations",
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Usage & Plan</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor your usage and manage your subscription
        </p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Crown
                className={`w-5 h-5 ${
                  isTrialPlan ? "text-muted-foreground" : "text-amber-500"
                }`}
              />
              <div>
                <CardTitle className="text-base">
                  {isTrialPlan ? "Trial Plan" : "Pro Plan"}
                </CardTitle>
                <CardDescription>
                  {isTrialPlan
                    ? "Limited features for evaluation"
                    : "Full access to all features"}
                </CardDescription>
              </div>
            </div>
            <Badge
              className={`${
                isTrialPlan
                  ? "bg-muted text-muted-foreground"
                  : "bg-amber-500/15 text-amber-600 dark:text-amber-400"
              }`}
            >
              {isTrialPlan ? "Trial" : "Pro"}
            </Badge>
          </div>
        </CardHeader>
      </Card>

      {/* Usage */}
      <div className="grid gap-4 md:grid-cols-2">
        {usageItems.map((item) => (
          <Card key={item.label}>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
                  <item.icon className={`w-4 h-4 ${item.color}`} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">
                    {item.label}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {item.used} / {item.limit}
                  </p>
                </div>
              </div>
              <Progress
                value={Math.min(item.percentage, 100)}
                className="h-2"
              />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Plan comparison */}
      {isTrialPlan && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Trial */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                Trial Plan
                <Badge variant="outline" className="text-xs">
                  Current
                </Badge>
              </CardTitle>
              <CardDescription>Basic features to get started</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2.5">
                {trialFeatures.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <Check className="w-4 h-4 text-muted-foreground/60" />
                    {feature}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Pro */}
          <Card className="border-primary/30 bg-primary/5 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full" />
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary" />
                Pro Plan
              </CardTitle>
              <CardDescription>Everything you need to scale</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2.5">
                {proFeatures.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-center gap-2 text-sm text-foreground"
                  >
                    <Check className="w-4 h-4 text-primary" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-md mt-4">
                Upgrade to Pro
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
