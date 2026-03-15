"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Settings,
  Key,
  Archive,
  Loader2,
  Copy,
  Plus,
  Trash2,
  RotateCcw,
  Eye,
  EyeOff,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

interface ApiKey {
  id: string;
  name: string;
  keyPrefix: string;
  createdAt: string;
  lastUsed: string | null;
  key?: string; // Only present on creation
}

export default function SettingsPage() {
  const params = useParams();
  const router = useRouter();
  const businessId = params.businessId as string;

  const [businessName, setBusinessName] = useState("");
  const [originalName, setOriginalName] = useState("");
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyDialogOpen, setNewKeyDialogOpen] = useState(false);
  const [creatingKey, setCreatingKey] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [deleteKeyTarget, setDeleteKeyTarget] = useState<{ id: string; name: string } | null>(null);
  const [rotateKeyTarget, setRotateKeyTarget] = useState<{ id: string; name: string } | null>(null);

  const fetchApiKeys = useCallback(async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}/api-keys`);
      if (res.ok) {
        const data = await res.json();
        setApiKeys(data);
      }
    } catch {
      toast.error("Failed to fetch API keys");
    } finally {
      setLoadingKeys(false);
    }
  }, [businessId]);

  useEffect(() => {
    // Fetch business details
    fetch("/api/businesses")
      .then((res) => res.json())
      .then((businesses) => {
        const biz = businesses.find(
          (b: { id: string }) => b.id === businessId
        );
        if (biz) {
          setBusinessName(biz.name);
          setOriginalName(biz.name);
        }
      });

    fetchApiKeys();
  }, [businessId, fetchApiKeys]);

  const handleSaveName = async () => {
    if (!businessName.trim() || businessName === originalName) return;
    setSaving(true);

    try {
      const res = await fetch(`/api/businesses/${businessId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: businessName }),
      });

      if (res.ok) {
        setOriginalName(businessName);
        toast.success("Business name updated");
        router.refresh();
      } else {
        const data = await res.json();
        toast.error(data.error || "Failed to update name");
      }
    } catch {
      toast.error("Failed to update name");
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    setArchiving(true);
    try {
      const res = await fetch(`/api/businesses/${businessId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "archived" }),
      });

      if (res.ok) {
        toast.success("Business archived");
        router.push("/");
      } else {
        toast.error("Failed to archive business");
      }
    } catch {
      toast.error("Failed to archive business");
    } finally {
      setArchiving(false);
    }
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return;
    setCreatingKey(true);

    try {
      const res = await fetch(`/api/businesses/${businessId}/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName }),
      });

      if (res.ok) {
        const data = await res.json();
        setNewlyCreatedKey(data.key);
        setNewKeyName("");
        fetchApiKeys();
        toast.success("API key created");
      } else {
        toast.error("Failed to create API key");
      }
    } catch {
      toast.error("Failed to create API key");
    } finally {
      setCreatingKey(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    try {
      const res = await fetch(
        `/api/businesses/${businessId}/api-keys?keyId=${keyId}`,
        { method: "DELETE" }
      );

      if (res.ok) {
        toast.success("API key deleted");
        fetchApiKeys();
      } else {
        toast.error("Failed to delete API key");
      }
    } catch {
      toast.error("Failed to delete API key");
    }
  };

  const handleRotateKey = async (keyId: string, keyName: string) => {
    // Delete old key
    await fetch(`/api/businesses/${businessId}/api-keys?keyId=${keyId}`, {
      method: "DELETE",
    });

    // Create new one with same name
    const res = await fetch(`/api/businesses/${businessId}/api-keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: keyName }),
    });

    if (res.ok) {
      const data = await res.json();
      setNewlyCreatedKey(data.key);
      setNewKeyDialogOpen(true);
      fetchApiKeys();
      toast.success("API key rotated");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your business settings and API keys
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general" className="gap-2">
            <Settings className="w-4 h-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="gap-2">
            <Key className="w-4 h-4" />
            API Keys
          </TabsTrigger>
        </TabsList>

        {/* General Tab */}
        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Business Name</CardTitle>
              <CardDescription>
                Change the display name of your business
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3">
                <Input
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="max-w-sm"
                />
                <Button
                  onClick={handleSaveName}
                  disabled={
                    saving || !businessName.trim() || businessName === originalName
                  }
                  className="bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Save"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Danger zone */}
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="text-base text-destructive flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Danger Zone
              </CardTitle>
              <CardDescription>
                Irreversible actions for your business
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Archive this business
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Archiving will disable the speech bot and all integrations
                  </p>
                </div>
                <Dialog>
                  <DialogTrigger
                    render={
                      <Button variant="outline" className="border-destructive/30 text-destructive hover:bg-destructive/10" />
                    }
                  >
                    <Archive className="w-4 h-4 mr-2" />
                    Archive
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Archive Business</DialogTitle>
                      <DialogDescription>
                        Are you sure you want to archive this business? The
                        speech bot will be disabled and all API keys will stop
                        working.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button variant="outline">Cancel</Button>
                      <Button
                        variant="destructive"
                        onClick={handleArchive}
                        disabled={archiving}
                      >
                        {archiving ? (
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        ) : null}
                        Archive Business
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">API Keys</CardTitle>
                  <CardDescription>
                    Manage API keys for integrating with your speech bot
                  </CardDescription>
                </div>
                <Dialog open={newKeyDialogOpen} onOpenChange={(open) => {
                  setNewKeyDialogOpen(open);
                  if (!open) {
                    setNewlyCreatedKey(null);
                    setShowKey(false);
                  }
                }}>
                  <DialogTrigger
                    render={
                      <Button
                        size="sm"
                        className="bg-primary hover:bg-primary/90 text-primary-foreground"
                      />
                    }
                  >
                    <Plus className="w-4 h-4 mr-1.5" />
                    Create Key
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>
                        {newlyCreatedKey ? "API Key Created" : "Create API Key"}
                      </DialogTitle>
                      <DialogDescription>
                        {newlyCreatedKey
                          ? "Copy your API key now. You won't be able to see it again."
                          : "Give your API key a descriptive name."}
                      </DialogDescription>
                    </DialogHeader>

                    {newlyCreatedKey ? (
                      <div className="space-y-3">
                        <div className="bg-muted rounded-lg p-3 font-mono text-sm break-all flex items-center gap-2">
                          <span className="flex-1 text-foreground">
                            {showKey ? newlyCreatedKey : "•".repeat(40)}
                          </span>
                          <div className="flex gap-1 shrink-0">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => setShowKey(!showKey)}
                            >
                              {showKey ? (
                                <EyeOff className="w-3.5 h-3.5" />
                              ) : (
                                <Eye className="w-3.5 h-3.5" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => copyToClipboard(newlyCreatedKey)}
                            >
                              <Copy className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                        <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 rounded-lg px-3 py-2 flex items-center gap-2">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          Store this key securely. It will not be shown again.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="space-y-2">
                          <Label htmlFor="keyName">Key Name</Label>
                          <Input
                            id="keyName"
                            placeholder="e.g. Production, Development"
                            value={newKeyName}
                            onChange={(e) => setNewKeyName(e.target.value)}
                            className=""
                          />
                        </div>
                        <DialogFooter>
                          <Button
                            onClick={handleCreateKey}
                            disabled={creatingKey || !newKeyName.trim()}
                            className="bg-primary hover:bg-primary/90 text-primary-foreground"
                          >
                            {creatingKey ? (
                              <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : null}
                            Create Key
                          </Button>
                        </DialogFooter>
                      </div>
                    )}
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {loadingKeys ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
              ) : apiKeys.length === 0 ? (
                <div className="text-center py-12">
                  <Key className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground font-medium">
                    No API keys yet
                  </p>
                  <p className="text-xs text-muted-foreground/70 mt-1">
                    Create an API key to integrate with your speech bot
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Key</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Last Used</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {apiKeys.map((key) => (
                      <TableRow key={key.id}>
                        <TableCell className="font-medium text-foreground">
                          {key.name}
                        </TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">
                            {key.keyPrefix}
                          </code>
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(key.createdAt).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {key.lastUsed
                            ? new Date(key.lastUsed).toLocaleDateString()
                            : "Never"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-muted-foreground hover:text-primary"
                              onClick={() =>
                                setRotateKeyTarget({ id: key.id, name: key.name })
                              }
                            >
                              <RotateCcw className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive hover:bg-destructive/10"
                              onClick={() => setDeleteKeyTarget({ id: key.id, name: key.name })}
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
        </TabsContent>
      </Tabs>

      {/* Delete API Key Confirmation */}
      <ConfirmDialog
        open={!!deleteKeyTarget}
        onOpenChange={(open) => !open && setDeleteKeyTarget(null)}
        title="Delete API Key"
        description={`Delete "${deleteKeyTarget?.name}"? Any integrations using it will stop working immediately.`}
        confirmLabel="Delete Key"
        variant="destructive"
        onConfirm={async () => {
          if (deleteKeyTarget) await handleDeleteKey(deleteKeyTarget.id);
        }}
      />

      {/* Rotate API Key Confirmation */}
      <ConfirmDialog
        open={!!rotateKeyTarget}
        onOpenChange={(open) => !open && setRotateKeyTarget(null)}
        title="Rotate API Key"
        description={`Rotate "${rotateKeyTarget?.name}"? The old key will stop working immediately and a new key will be generated.`}
        confirmLabel="Rotate Key"
        variant="default"
        onConfirm={async () => {
          if (rotateKeyTarget)
            await handleRotateKey(rotateKeyTarget.id, rotateKeyTarget.name);
        }}
      />
    </div>
  );
}
