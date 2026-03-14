import { auth } from "@/auth";
import { db } from "@/db";
import { businesses } from "@/db/schema";
import { eq } from "drizzle-orm";
import { redirect } from "next/navigation";
import { SidebarNav } from "@/components/sidebar-nav";
import { BusinessSwitcher } from "@/components/business-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { signOut } from "@/auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LogOut } from "lucide-react";

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ businessId: string }>;
}) {
  const session = await auth();
  if (!session?.user?.id) redirect("/auth/signin");

  const { businessId } = await params;

  const userBusinesses = await db
    .select()
    .from(businesses)
    .where(eq(businesses.ownerId, session.user.id));

  if (userBusinesses.length === 0) redirect("/onboarding");

  const currentBusiness = userBusinesses.find((b) => b.id === businessId);
  if (!currentBusiness) redirect(`/dashboard/${userBusinesses[0].id}`);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plan = ((session.user as any).plan as string) || "trial";

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="w-[240px] bg-sidebar border-r border-sidebar-border flex flex-col shrink-0">
        <SidebarNav businessId={businessId} plan={plan} />
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-border bg-card/80 backdrop-blur-sm flex items-center justify-between px-6 shrink-0">
          <BusinessSwitcher
            businesses={userBusinesses}
            currentBusinessId={businessId}
            plan={plan}
          />

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger className="focus:outline-none">
                <Avatar className="w-8 h-8 border border-border cursor-pointer">
                  <AvatarImage src={session.user.image || ""} />
                  <AvatarFallback className="bg-primary/15 text-primary text-xs">
                    {session.user.name?.charAt(0) || "U"}
                  </AvatarFallback>
                </Avatar>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium text-foreground">
                    {session.user.name}
                  </p>
                  <p className="text-xs text-muted-foreground">{session.user.email}</p>
                </div>
                <DropdownMenuSeparator />
                <form
                    action={async () => {
                      "use server";
                      await signOut({ redirectTo: "/auth/signin" });
                    }}
                  >
                    <DropdownMenuItem
                      render={<button type="submit" className="w-full cursor-pointer" />}
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </DropdownMenuItem>
                  </form>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
