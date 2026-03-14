import { auth } from "@/auth";
import { db } from "@/db";
import { businesses } from "@/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";
import { getPlanLimits } from "@/lib/plans";
import type { PlanType } from "@/lib/plans";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const userBusinesses = await db
    .select()
    .from(businesses)
    .where(eq(businesses.ownerId, session.user.id));

  return NextResponse.json(userBusinesses);
}

export async function POST(req: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { name, type, goal } = await req.json();

  if (!name || !type || !goal) {
    return NextResponse.json(
      { error: "Name, type, and goal are required" },
      { status: 400 }
    );
  }

  // Check plan limits
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plan = ((session.user as any).plan as PlanType) || "trial";
  const limits = getPlanLimits(plan);

  const existingBusinesses = await db
    .select()
    .from(businesses)
    .where(eq(businesses.ownerId, session.user.id));

  if (existingBusinesses.length >= limits.maxBusinesses) {
    return NextResponse.json(
      {
        error: `Your ${plan} plan allows only ${limits.maxBusinesses} business(es). Upgrade to Pro for more.`,
      },
      { status: 403 }
    );
  }

  // Check uniqueness
  const existing = await db
    .select()
    .from(businesses)
    .where(eq(businesses.name, name));

  if (existing.length > 0) {
    return NextResponse.json(
      { error: "A business with this name already exists" },
      { status: 409 }
    );
  }

  const [business] = await db
    .insert(businesses)
    .values({
      name,
      type,
      goal,
      ownerId: session.user.id,
    })
    .returning();

  return NextResponse.json(business, { status: 201 });
}
