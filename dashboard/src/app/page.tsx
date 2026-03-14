import { auth } from "@/auth";
import { db } from "@/db";
import { businesses } from "@/db/schema";
import { eq } from "drizzle-orm";
import { redirect } from "next/navigation";

export default async function HomePage() {
  const session = await auth();

  if (!session?.user?.id) {
    redirect("/auth/signin");
  }

  // Check if user has any businesses
  const userBusinesses = await db
    .select()
    .from(businesses)
    .where(eq(businesses.ownerId, session.user.id));

  if (userBusinesses.length === 0) {
    redirect("/onboarding");
  }

  // Redirect to first business
  redirect(`/dashboard/${userBusinesses[0].id}`);
}
