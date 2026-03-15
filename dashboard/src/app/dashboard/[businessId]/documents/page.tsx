"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { UpgradeBanner } from "@/components/upgrade-banner";
import {
  FileText,
  Upload,
  Trash2,
  Loader2,
  FileUp,
  AlertCircle,
  File,
  Eye,
  X,
} from "lucide-react";
import { toast } from "sonner";

interface Document {
  id: string;
  name: string;
  fileUrl: string;
  size: number;
  mimeType: string;
  ingestionStatus: string;
  active: boolean;
  createdAt: string;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const params = useParams();
  const businessId = params.businessId as string;
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<{ doc: Document, url: string | null } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch {
      toast.error("Failed to fetch documents");
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const allowedTypes = [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    setUploading(true);

    for (const file of Array.from(files)) {
      if (!allowedTypes.includes(file.type)) {
        toast.error(`${file.name}: Only PDF, DOC, DOCX allowed`);
        continue;
      }

      try {
        // Step 1: Get presigned URL (no DB entry yet)
        const res = await fetch(`/api/businesses/${businessId}/documents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            fileName: file.name,
            fileSize: file.size,
            mimeType: file.type,
          }),
        });

        const data = await res.json();

        if (!res.ok) {
          toast.error(data.error || `Failed to upload ${file.name}`);
          continue;
        }

        // Step 2: Upload to S3
        const uploadRes = await fetch(data.uploadUrl, {
          method: "PUT",
          body: file,
          headers: { "Content-Type": file.type },
        });

        if (!uploadRes.ok) {
          toast.error(`Failed to upload ${file.name} to storage`);
          continue;
        }

        // Step 3: Confirm upload — creates DB entry only on success
        const confirmRes = await fetch(`/api/businesses/${businessId}/documents`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            fileKey: data.fileKey,
            fileUrl: data.fileUrl,
            fileName: data.fileName,
            fileSize: data.fileSize,
            mimeType: data.mimeType,
          }),
        });

        if (confirmRes.ok) {
          toast.success(`${file.name} uploaded successfully`);
        } else {
          toast.error(`Failed to save ${file.name}`);
        }
      } catch {
        toast.error(`Failed to upload ${file.name}`);
      }
    }

    setUploading(false);
    setDialogOpen(false);
    fetchDocuments();
  };

  const handleDelete = async (docId: string) => {
    try {
      const res = await fetch(
        `/api/businesses/${businessId}/documents?documentId=${docId}`,
        { method: "DELETE" }
      );

      if (res.ok) {
        toast.success("Document deleted");
        fetchDocuments();
      } else {
        toast.error("Failed to delete document");
      }
    } catch {
      toast.error("Failed to delete document");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  const totalSize = documents.reduce((acc, d) => acc + d.size, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Documents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Upload and manage your knowledge base documents
          </p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm" />
            }
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Documents
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Documents</DialogTitle>
              <DialogDescription>
                Upload PDF, DOC, or DOCX files. They will be processed and added
                to your knowledge base.
              </DialogDescription>
            </DialogHeader>
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                dragOver
                  ? "border-primary bg-primary/5"
                  : "border-border bg-muted/30"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <FileUp className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-foreground mb-1">
                Drag & drop files here, or
              </p>
              <label className="cursor-pointer">
                <span className="text-sm text-primary hover:text-primary/80 font-medium">
                  browse files
                </span>
                <input
                  type="file"
                  className="hidden"
                  multiple
                  accept=".pdf,.doc,.docx"
                  onChange={(e) => handleUpload(e.target.files)}
                  disabled={uploading}
                />
              </label>
              <p className="text-xs text-muted-foreground mt-2">
                PDF, DOC, DOCX • Max 100 MB total (trial)
              </p>
            </div>
            {uploading && (
              <div className="flex items-center justify-center gap-2 py-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">Uploading...</span>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>

      {/* Storage indicator */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Storage: {formatSize(totalSize)} / 100 MB
            </span>
            <span className="text-muted-foreground">
              {documents.length} document(s)
            </span>
          </div>
          <div className="w-full bg-muted rounded-full h-2 mt-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  (totalSize / (100 * 1024 * 1024)) * 100,
                  100
                )}%`,
              }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Documents table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">All Documents</CardTitle>
          <CardDescription>
            Manage your uploaded documents and their processing status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12">
              <File className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground font-medium">
                No documents yet
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Upload your first document to get started
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-500 dark:text-blue-400 shrink-0" />
                        <span className="font-medium text-foreground truncate max-w-[200px]">
                          {doc.name}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatSize(doc.size)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-xs ${
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
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(doc.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-muted-foreground hover:text-primary"
                          onClick={async () => {
                            if (doc.mimeType !== "application/pdf") {
                              setPreviewDoc({ doc, url: null });
                              return;
                            }
                            
                            try {
                              const res = await fetch(`/api/businesses/${businessId}/documents/${doc.id}/url`);
                              const data = await res.json();
                              
                              if (!res.ok) {
                                throw new Error(data.error || "Failed to load preview");
                              }
                              
                              setPreviewDoc({ doc, url: data.url });
                            } catch (err: any) {
                              console.error("Preview error:", err);
                              toast.error(err.message || "Could not load document preview");
                            }
                          }}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => setDeleteTarget({ id: doc.id, name: doc.name })}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Document"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={async () => { if (deleteTarget) await handleDelete(deleteTarget.id); }}
      />

      {/* Preview Dialog */}
      <Dialog open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)}>
        <DialogContent className="!w-[90vw] !max-w-[90vw] !h-[90vh] !max-h-[90vh] flex flex-col p-6">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 pr-8">
              <FileText className="w-4 h-4 text-blue-500 dark:text-blue-400 shrink-0" />
              <span className="truncate">{previewDoc?.doc.name}</span>
            </DialogTitle>
            <DialogDescription>
              {previewDoc && formatSize(previewDoc.doc.size)} • {previewDoc?.doc.mimeType === "application/pdf" ? "PDF" : "Document"}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 min-h-0 rounded-lg overflow-hidden border border-border bg-muted/30">
            {previewDoc?.url && previewDoc?.doc.mimeType === "application/pdf" ? (
              <iframe
                src={previewDoc.url}
                className="h-full w-full border-0 bg-white"
                title={`Preview: ${previewDoc.doc.name}`}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-[40vh] text-center p-6">
                <File className="w-12 h-12 text-muted-foreground/30 mb-3" />
                <p className="text-sm font-medium text-foreground">
                  Preview not available for this format
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  DOC/DOCX files cannot be previewed in the browser.
                  Download to view.
                </p>
                <a
                  href={previewDoc?.doc.fileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                >
                  Download File
                </a>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
