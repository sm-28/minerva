import { auth } from "@/auth";
import { db } from "@/db";
import { businesses, documents } from "@/db/schema";
import { eq } from "drizzle-orm";
import { redirect } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { UpgradeBanner } from "@/components/upgrade-banner";
import {
  FileText,
  BarChart3,
  MessageSquare,
  Mic,
  ArrowUpRight,
  Activity,
} from "lucide-react";
import Link from "next/link";

export default async function OverviewPage({
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

  const docs = await db
    .select()
    .from(documents)
    .where(eq(documents.businessId, businessId));

  const totalDocs = docs.length;
  const activeDocs = docs.filter((d) => d.active).length;
  const totalSize = docs.reduce((acc, d) => acc + d.size, 0);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plan = ((session.user as any).plan as string) || "trial";

  const stats = [
    {
      title: "Documents",
      value: totalDocs.toString(),
      description: `${activeDocs} active`,
      icon: FileText,
      color: "text-blue-500 dark:text-blue-400",
      bgColor: "bg-blue-500/10",
      href: `/dashboard/${businessId}/documents`,
    },
    {
      title: "Storage Used",
      value:
        totalSize > 1024 * 1024
          ? `${(totalSize / (1024 * 1024)).toFixed(1)} MB`
          : `${(totalSize / 1024).toFixed(1)} KB`,
      description: plan === "trial" ? "of 100 MB limit" : "of 10 GB limit",
      icon: BarChart3,
      color: "text-emerald-500 dark:text-emerald-400",
      bgColor: "bg-emerald-500/10",
      href: `/dashboard/${businessId}/usage`,
    },
    {
      title: "Text Chats",
      value: plan === "trial" ? "10" : "∞",
      description: plan === "trial" ? "trial limit" : "credits-based",
      icon: MessageSquare,
      color: "text-violet-500 dark:text-violet-400",
      bgColor: "bg-violet-500/10",
      href: `/dashboard/${businessId}/testing`,
    },
    {
      title: "Speech Chats",
      value: plan === "trial" ? "10" : "∞",
      description: plan === "trial" ? "trial limit" : "credits-based",
      icon: Mic,
      color: "text-amber-500 dark:text-amber-400",
      bgColor: "bg-amber-500/10",
      href: `/dashboard/${businessId}/testing`,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          {business.name}
        </h1>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="outline" className="text-xs capitalize">
            {business.type.replace("_", " ")}
          </Badge>
          <Badge variant="outline" className="text-xs capitalize">
            {business.goal.replace("_", " ")}
          </Badge>
          <Badge
            variant="outline"
            className={`text-xs ${
              business.status === "active"
                ? "border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                : "text-muted-foreground"
            }`}
          >
            {business.status}
          </Badge>
        </div>
      </div>

      {/* Trial upgrade banner */}
      {plan === "trial" && (
        <UpgradeBanner
          businessId={businessId}
          message="You're on the trial plan. Upgrade to Pro for unlimited businesses, more storage, and credits-based usage."
        />
      )}

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.title} href={stat.href}>
            <Card className="hover:shadow-md transition-shadow duration-200 cursor-pointer group">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <div
                  className={`w-8 h-8 rounded-lg ${stat.bgColor} flex items-center justify-center`}
                >
                  <stat.icon className={`w-4 h-4 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-foreground">
                  {stat.value}
                </div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  {stat.description}
                  <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="w-4 h-4 text-muted-foreground" />
            Recent Activity
          </CardTitle>
          <CardDescription>Your latest actions and events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {docs.length > 0 ? (
              docs.slice(0, 5).map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 text-sm"
                >
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">
                      {doc.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(doc.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-xs shrink-0 ${
                      doc.ingestionStatus === "completed"
                        ? "border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                        : doc.ingestionStatus === "processing"
                        ? "border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/10"
                        : doc.ingestionStatus === "failed"
                        ? "border-red-500/30 text-red-600 dark:text-red-400 bg-red-500/10"
                        : "text-muted-foreground"
                    }`}
                  >
                    {doc.ingestionStatus}
                  </Badge>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <FileText className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">No activity yet</p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  Upload documents to get started
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
