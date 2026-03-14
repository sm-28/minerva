import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Zap } from "lucide-react";

interface UpgradeBannerProps {
  businessId: string;
  message?: string;
  variant?: "full" | "compact";
}

export function UpgradeBanner({
  businessId,
  message = "Upgrade to Pro for more features.",
  variant = "full",
}: UpgradeBannerProps) {
  if (variant === "compact") {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10 border border-primary/20">
        <Zap className="w-3.5 h-3.5 text-primary shrink-0" />
        <span className="text-xs text-foreground flex-1">{message}</span>
        <Link href={`/dashboard/${businessId}/usage`}>
          <Button size="sm" variant="outline" className="h-6 text-xs border-primary/30 text-primary hover:bg-primary/10">
            Upgrade
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-primary/20 bg-primary/5 p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center">
            <Zap className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              Upgrade to Pro
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">{message}</p>
          </div>
        </div>
        <Link href={`/dashboard/${businessId}/usage`}>
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm">
            Upgrade Now
          </Button>
        </Link>
      </div>
    </div>
  );
}
