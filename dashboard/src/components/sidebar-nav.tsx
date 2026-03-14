"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  BarChart3,
  Settings,
  Bot,
  Crown,
  Zap,
} from "lucide-react";

interface SidebarNavProps {
  businessId: string;
  plan: string;
}

const navItems = [
  { title: "Overview", href: "", icon: LayoutDashboard },
  { title: "Documents", href: "/documents", icon: FileText },
  { title: "Testing", href: "/testing", icon: MessageSquare },
  { title: "Usage", href: "/usage", icon: BarChart3 },
  { title: "Settings", href: "/settings", icon: Settings },
];

export function SidebarNav({ businessId, plan }: SidebarNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const basePath = `/dashboard/${businessId}`;

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 pb-2">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shadow-md shadow-emerald-900/40">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-foreground text-lg">Minerva</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map((item) => {
          const fullHref = basePath + item.href;
          const isActive =
            item.href === ""
              ? pathname === basePath
              : pathname.startsWith(fullHref);

          return (
            <Link
              key={item.title}
              href={fullHref}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-emerald-500/15 text-emerald-400"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <item.icon
                className={cn(
                  "w-4 h-4 shrink-0",
                  isActive ? "text-emerald-400" : "text-muted-foreground"
                )}
              />
              {item.title}
            </Link>
          );
        })}
      </nav>

      {/* Plan section */}
      <div className="p-3 border-t border-border flex flex-col gap-2">
        {plan === "trial" ? (
          <>
            <div className="px-2 pt-1 pb-1 flex items-center justify-center gap-2">
              <Crown className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground">Trial Plan</span>
            </div>
            <button
              onClick={() => router.push(`/dashboard/${businessId}/usage`)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-primary/10 hover:bg-primary/15 border border-primary/20 transition-all duration-150 group cursor-pointer"
            >
              <Zap className="w-4 h-4 text-primary shrink-0 group-hover:scale-110 transition-transform" />
              <div className="flex-1 text-left min-w-0">
                <p className="text-xs font-semibold text-primary">Upgrade to Pro</p>
                <p className="text-xs text-muted-foreground truncate">Unlock all features</p>
              </div>
            </button>
          </>
        ) : (
          <div className="flex items-center gap-3 px-3 py-2.5">
            <Crown className="w-4 h-4 text-amber-500 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-foreground">Pro Plan</p>
              <p className="text-xs text-muted-foreground">All features active</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
