import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import { db } from "@/db";
import { users, accounts, sessions, verificationTokens } from "@/db/schema";

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: DrizzleAdapter(db, {
    usersTable: users,
    accountsTable: accounts,
    sessionsTable: sessions,
    verificationTokensTable: verificationTokens,
  }),
  providers: [Google],
  pages: {
    signIn: "/auth/signin",
  },
  callbacks: {
    async session({ session, user }) {
      if (session.user) {
        session.user.id = user.id;
        // Fetch plan from db
        const dbUser = await db.query.users.findFirst({
          where: (u, { eq }) => eq(u.id, user.id),
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (session.user as any).plan = dbUser?.plan ?? "trial";
      }
      return session;
    },
  },
});
