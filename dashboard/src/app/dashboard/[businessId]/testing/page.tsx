"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UpgradeBanner } from "@/components/upgrade-banner";
import {
  Send,
  Mic,
  MicOff,
  Bot,
  User,
  Volume2,
  MessageSquare,
  Sparkles,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: "text" | "speech";
  timestamp: Date;
}

const SAMPLE_RESPONSES = [
  "Hello! I'm Minerva, your AI speech assistant. How can I help you today?",
  "Based on your documents, I can see that the warehouse operations have been running at 85% capacity. Would you like me to provide a detailed breakdown?",
  "I've analyzed the customer support tickets from last week. The most common issues were related to billing inquiries and shipment tracking.",
  "The lead generation metrics show a 23% improvement compared to the previous quarter. I can share more specific insights about which channels performed best.",
  "I can help you with that! Let me review the relevant documents and get back to you with the information you need.",
];

export default function TestingPage() {
  const params = useParams();
  const businessId = params.businessId as string;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSpeechMode, setIsSpeechMode] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [textChatsUsed, setTextChatsUsed] = useState(0);
  const [speechChatsUsed, setSpeechChatsUsed] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (content: string, mode: "text" | "speech") => {
    if (!content.trim()) return;
    if (mode === "text" && textChatsUsed >= 10) return;
    if (mode === "speech" && speechChatsUsed >= 10) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      mode,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsThinking(true);

    await new Promise((resolve) => setTimeout(resolve, 1500));

    const responseText =
      SAMPLE_RESPONSES[Math.floor(Math.random() * SAMPLE_RESPONSES.length)];

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: responseText,
      mode,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsThinking(false);

    if (mode === "text") setTextChatsUsed((prev) => prev + 1);
    else setSpeechChatsUsed((prev) => prev + 1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input, "text");
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      setTimeout(() => {
        sendMessage(
          "This is a simulated speech transcript. In production, this would use your speech-to-text service.",
          "speech"
        );
      }, 500);
    } else {
      if (speechChatsUsed >= 10) return;
      setIsRecording(true);
    }
  };

  return (
    <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Testing</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Test your AI speech bot with text or voice
          </p>
        </div>

        {/* Mode toggle */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-card rounded-lg border border-border px-3 py-2">
            <MessageSquare
              className={`w-4 h-4 ${
                !isSpeechMode ? "text-primary" : "text-muted-foreground"
              }`}
            />
            <Switch
              checked={isSpeechMode}
              onCheckedChange={setIsSpeechMode}
            />
            <Mic
              className={`w-4 h-4 ${
                isSpeechMode ? "text-primary" : "text-muted-foreground"
              }`}
            />
          </div>
          <Badge variant="outline" className="text-xs">
            {isSpeechMode ? "Speech Mode" : "Text Mode"}
          </Badge>
        </div>
      </div>

      {/* Usage indicators */}
      <div className="flex gap-3 shrink-0">
        <Badge
          variant="outline"
          className={`text-xs ${
            textChatsUsed >= 10
              ? "border-red-500/30 text-red-600 dark:text-red-400 bg-red-500/10"
              : ""
          }`}
        >
          Text: {textChatsUsed}/10
        </Badge>
        <Badge
          variant="outline"
          className={`text-xs ${
            speechChatsUsed >= 10
              ? "border-red-500/30 text-red-600 dark:text-red-400 bg-red-500/10"
              : ""
          }`}
        >
          Speech: {speechChatsUsed}/10
        </Badge>
        {(textChatsUsed >= 8 || speechChatsUsed >= 8) && (
          <UpgradeBanner
            businessId={businessId}
            message="Running low on trial chats"
            variant="compact"
          />
        )}
      </div>

      {/* Chat area */}
      <Card className="flex-1 flex flex-col overflow-hidden">
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                Start a conversation
              </h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                {isSpeechMode
                  ? "Click the microphone button to start speaking"
                  : "Type a message below to begin chatting with Minerva"}
              </p>
              <p className="text-xs text-muted-foreground mt-4 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5">
                ⚠️ Prototype mode — responses are simulated
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0 shadow-sm">
                      <Bot className="w-4 h-4 text-primary-foreground" />
                    </div>
                  )}
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground rounded-br-md"
                        : "bg-muted text-foreground rounded-bl-md"
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    <div
                      className={`flex items-center gap-1.5 mt-1.5 text-xs ${
                        message.role === "user"
                          ? "text-primary-foreground/60"
                          : "text-muted-foreground"
                      }`}
                    >
                      {message.mode === "speech" && (
                        <Volume2 className="w-3 h-3" />
                      )}
                      <span>
                        {message.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>
                  {message.role === "user" && (
                    <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                      <User className="w-4 h-4 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}

              {isThinking && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0 shadow-sm">
                    <Bot className="w-4 h-4 text-primary-foreground" />
                  </div>
                  <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />
                      <div
                        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                        style={{ animationDelay: "0.1s" }}
                      />
                      <div
                        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Input area */}
        <div className="border-t border-border p-4 bg-card/50">
          {isSpeechMode ? (
            <div className="flex flex-col items-center gap-3">
              <button
                onClick={toggleRecording}
                disabled={speechChatsUsed >= 10}
                className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 cursor-pointer ${
                  isRecording
                    ? "bg-red-500 shadow-lg shadow-red-500/25 scale-110"
                    : speechChatsUsed >= 10
                    ? "bg-muted cursor-not-allowed"
                    : "bg-primary shadow-lg shadow-primary/25 hover:scale-105"
                }`}
              >
                {isRecording ? (
                  <MicOff className="w-6 h-6 text-white" />
                ) : (
                  <Mic className="w-6 h-6 text-primary-foreground" />
                )}
              </button>
              <p className="text-xs text-muted-foreground">
                {isRecording
                  ? "Recording... Click to stop"
                  : speechChatsUsed >= 10
                  ? "Trial limit reached"
                  : "Click to start recording"}
              </p>
              {isRecording && (
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1 bg-red-400 rounded-full animate-pulse"
                      style={{
                        height: `${Math.random() * 24 + 8}px`,
                        animationDelay: `${i * 0.1}s`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  textChatsUsed >= 10
                    ? "Trial limit reached. Upgrade to Pro for more."
                    : "Type your message..."
                }
                disabled={textChatsUsed >= 10}
                className="resize-none min-h-[44px] max-h-[120px]"
                rows={1}
              />
              <Button
                onClick={() => sendMessage(input, "text")}
                disabled={!input.trim() || textChatsUsed >= 10}
                className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm shrink-0"
                size="icon"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
