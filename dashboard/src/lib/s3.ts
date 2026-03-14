import { S3Client } from "@aws-sdk/client-s3";

export const s3Client = new S3Client({
  // Alibaba Cloud OSS/AWS S3 endpoint (S3-compatible)
  endpoint: process.env.S3_ENDPOINT!,
  region: process.env.S3_REGION!,
  credentials: {
    accessKeyId: process.env.S3_ACCESS_KEY_ID!,
    secretAccessKey: process.env.S3_SECRET_ACCESS_KEY!,
  },
  forcePathStyle: process.env.S3_FORCE_PATH_STYLE === "true", // Required for S3-compatible services
});

export const S3_BUCKET = process.env.S3_BUCKET!;
