import { Loader2 } from "lucide-react";

export default function DashboardLoading() {
  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-card shadow-sm">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">Loading page</p>
          <p className="text-xs text-muted-foreground">
            Fetching the latest dashboard data...
          </p>
        </div>
      </div>
    </div>
  );
}
