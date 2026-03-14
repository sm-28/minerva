import { auth } from "@/auth";
import { db } from "@/db";
import { documents, businesses } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { NextResponse } from "next/server";
import { GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { s3Client, S3_BUCKET } from "@/lib/s3";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ businessId: string; documentId: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { businessId, documentId } = await params;

    // Verify ownership
    const [business] = await db
      .select()
      .from(businesses)
      .where(
        and(eq(businesses.id, businessId), eq(businesses.ownerId, session.user.id))
      );

    if (!business) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    // Get document metadata
    const [doc] = await db
      .select()
      .from(documents)
      .where(
        and(eq(documents.id, documentId), eq(documents.businessId, businessId))
      );

    if (!doc) {
      return NextResponse.json({ error: "Document not found" }, { status: 404 });
    }

    // Generate short-lived presigned GET URL (expires in 15 minutes)
    const command = new GetObjectCommand({
      Bucket: S3_BUCKET,
      Key: doc.fileKey,
      ResponseContentType: doc.mimeType,
      ResponseContentDisposition: "inline", // Forces browser to display PDF instead of downloading
    });

    const viewUrl = await getSignedUrl(s3Client, command, {
      expiresIn: 900,
    });

    return NextResponse.json({ url: viewUrl });
  } catch (error) {
    console.error("Error generating view URL:", error);
    return NextResponse.json(
      { error: "Failed to generate view URL" },
      { status: 500 }
    );
  }
}
