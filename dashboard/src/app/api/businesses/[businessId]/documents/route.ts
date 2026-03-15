import { auth } from "@/auth";
import { db } from "@/db";
import { documents, businesses } from "@/db/schema";
import { eq, and, sum } from "drizzle-orm";
import { NextResponse } from "next/server";
import { PutObjectCommand, DeleteObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { s3Client, S3_BUCKET } from "@/lib/s3";
import { getPlanLimits } from "@/lib/plans";
import type { PlanType } from "@/lib/plans";
import { randomUUID } from "crypto";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ businessId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { businessId } = await params;

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

  const docs = await db
    .select()
    .from(documents)
    .where(eq(documents.businessId, businessId));

  return NextResponse.json(docs);
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ businessId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { businessId } = await params;
  const { fileName, fileSize, mimeType } = await req.json();

  // Validate file type
  const allowedTypes = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ];

  if (!allowedTypes.includes(mimeType)) {
    return NextResponse.json(
      { error: "Only PDF, DOC, and DOCX files are allowed" },
      { status: 400 }
    );
  }

  // Check plan storage limits
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plan = ((session.user as any).plan as PlanType) || "trial";
  const limits = getPlanLimits(plan);

  const [storageResult] = await db
    .select({ totalSize: sum(documents.size) })
    .from(documents)
    .where(eq(documents.businessId, businessId));

  const currentStorage = Number(storageResult?.totalSize || 0);
  const maxBytes = limits.maxDocumentStorageMB * 1024 * 1024;

  if (currentStorage + fileSize > maxBytes) {
    return NextResponse.json(
      {
        error: `Storage limit reached (${limits.maxDocumentStorageMB} MB on ${plan} plan). Upgrade to Pro for more storage.`,
      },
      { status: 403 }
    );
  }

  // Generate S3 key and presigned URL (no DB entry yet)
  const fileKey = `${businessId}/${randomUUID()}-${fileName}`;

  const command = new PutObjectCommand({
    Bucket: S3_BUCKET,
    Key: fileKey,
    ContentType: mimeType,
    ContentLength: fileSize,
  });

  const uploadUrl = await getSignedUrl(s3Client, command, {
    expiresIn: 3600,
  });

  const fileUrl = `${process.env.S3_ENDPOINT}/${S3_BUCKET}/${fileKey}`;

  // Return presigned URL + metadata for the client to upload, then confirm
  return NextResponse.json({
    uploadUrl,
    fileKey,
    fileUrl,
    fileName,
    fileSize,
    mimeType,
  });
}

// Step 2: Confirm upload — creates DB entry only after successful S3 upload
export async function PUT(
  req: Request,
  { params }: { params: Promise<{ businessId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { businessId } = await params;
  const { fileKey, fileUrl, fileName, fileSize, mimeType } = await req.json();

  if (!fileKey || !fileUrl || !fileName || !fileSize || !mimeType) {
    return NextResponse.json(
      { error: "Missing required fields" },
      { status: 400 }
    );
  }

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

  const [doc] = await db
    .insert(documents)
    .values({
      businessId,
      name: fileName,
      fileKey,
      fileUrl,
      size: fileSize,
      mimeType,
      ingestionStatus: "pending",
    })
    .returning();

  return NextResponse.json({ document: doc }, { status: 201 });
}

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ businessId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { businessId } = await params;
  const { searchParams } = new URL(req.url);
  const documentId = searchParams.get("documentId");

  if (!documentId) {
    return NextResponse.json(
      { error: "Document ID is required" },
      { status: 400 }
    );
  }

  // Get document
  const [doc] = await db
    .select()
    .from(documents)
    .where(
      and(eq(documents.id, documentId), eq(documents.businessId, businessId))
    );

  if (!doc) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }

  // Delete from S3
  try {
    await s3Client.send(
      new DeleteObjectCommand({
        Bucket: S3_BUCKET,
        Key: doc.fileKey,
      })
    );
  } catch {
    // Continue even if S3 delete fails
    console.error("Failed to delete from S3");
  }

  // Delete from DB
  await db.delete(documents).where(eq(documents.id, documentId));

  return NextResponse.json({ success: true });
}
