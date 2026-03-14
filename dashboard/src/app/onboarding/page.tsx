"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Bot, Loader2, Sparkles, ArrowRight } from "lucide-react";

const BUSINESS_TYPES = [
  { value: "warehouse", label: "Warehouse" },
  { value: "fintech", label: "Fintech" },
  { value: "real_estate", label: "Real Estate" },
  { value: "custom", label: "Custom" },
];

const BUSINESS_GOALS = [
  { value: "leads", label: "Lead Generation" },
  { value: "customer_support", label: "Customer Support" },
  { value: "sales", label: "Sales Assistance" },
  { value: "onboarding", label: "User Onboarding" },
  { value: "feedback", label: "Feedback Collection" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<"form" | "initializing" | "done">("form");
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [goal, setGoal] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/businesses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, type, goal }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Something went wrong");
        setLoading(false);
        return;
      }

      setStep("initializing");
      await new Promise((resolve) => setTimeout(resolve, 3000));

      setStep("done");
      setTimeout(() => {
        router.push(`/dashboard/${data.id}`);
      }, 500);
    } catch {
      setError("Failed to create business. Please try again.");
      setLoading(false);
    }
  }

  if (step === "initializing" || step === "done") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-6">
          <div className="relative inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary shadow-lg shadow-primary/20">
            <Bot className="w-10 h-10 text-primary-foreground" />
            {step === "initializing" && (
              <div className="absolute inset-0 rounded-2xl border-2 border-primary/50 animate-ping" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              {step === "initializing"
                ? "Setting up your project..."
                : "All set!"}
            </h2>
            <p className="text-muted-foreground mt-2">
              {step === "initializing"
                ? "Configuring your AI speech bot. This will only take a moment."
                : "Redirecting you to your dashboard..."}
            </p>
          </div>
          {step === "initializing" && (
            <div className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span className="text-sm text-primary">Initializing...</span>
            </div>
          )}
          {step === "done" && (
            <div className="flex items-center justify-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              <span className="text-sm text-emerald-600 dark:text-emerald-400">Ready!</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg shadow-xl">
        <CardHeader className="text-center space-y-1 pb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary mx-auto mb-2 shadow-lg shadow-primary/20">
            <Bot className="w-6 h-6 text-primary-foreground" />
          </div>
          <CardTitle className="text-xl">Create Your First Business</CardTitle>
          <CardDescription>
            Set up your AI speech bot in just a few steps
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="name">Business Name</Label>
              <Input
                id="name"
                placeholder="e.g. Acme Corp"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Must be unique across all users
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">Business Type</Label>
              <Select value={type} onValueChange={(v) => setType(v ?? "")} required>
                <SelectTrigger id="type">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {BUSINESS_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="goal">Primary Goal</Label>
              <Select value={goal} onValueChange={(v) => setGoal(v ?? "")} required>
                <SelectTrigger id="goal">
                  <SelectValue placeholder="Select goal" />
                </SelectTrigger>
                <SelectContent>
                  {BUSINESS_GOALS.map((g) => (
                    <SelectItem key={g.value} value={g.value}>
                      {g.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-md"
              disabled={loading || !name || !type || !goal}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  Create Business
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
