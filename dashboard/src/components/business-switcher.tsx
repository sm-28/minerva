"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ChevronsUpDown, Building2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

interface Business {
  id: string;
  name: string;
  type: string;
  status: string;
}

interface BusinessSwitcherProps {
  businesses: Business[];
  currentBusinessId: string;
  plan: string;
}

export function BusinessSwitcher({
  businesses,
  currentBusinessId,
  plan,
}: BusinessSwitcherProps) {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const currentBusiness = businesses.find((b) => b.id === currentBusinessId);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-[220px] justify-between bg-secondary/50 border-border hover:bg-secondary"
          />
        }
      >
        <div className="flex items-center gap-2 truncate">
          <Building2 className="h-4 w-4 shrink-0 text-primary" />
          <span className="truncate text-foreground">
            {currentBusiness?.name || "Select business"}
          </span>
        </div>
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </PopoverTrigger>
      <PopoverContent className="w-[220px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search business..." />
          <CommandList>
            <CommandEmpty>No businesses found.</CommandEmpty>
            <CommandGroup>
              {businesses.map((business) => (
                <CommandItem
                  key={business.id}
                  value={business.name}
                  onSelect={() => {
                    router.push(`/dashboard/${business.id}`);
                    setOpen(false);
                  }}
                >
                  <Building2 className="mr-2 h-4 w-4 text-muted-foreground" />
                  <span className="truncate">{business.name}</span>
                  <Check
                    className={cn(
                      "ml-auto h-4 w-4 text-primary",
                      business.id === currentBusinessId
                        ? "opacity-100"
                        : "opacity-0"
                    )}
                  />
                </CommandItem>
              ))}
            </CommandGroup>
            {plan !== "trial" ? (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => {
                      router.push("/onboarding");
                      setOpen(false);
                    }}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    New Business
                  </CommandItem>
                </CommandGroup>
              </>
            ) : (
              <>
                <CommandSeparator />
                <CommandGroup heading="Trial Plan">
                  <CommandItem
                    onSelect={() => {
                      router.push(`/dashboard/${currentBusinessId}/usage`);
                      setOpen(false);
                    }}
                    className="text-primary"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Upgrade to add more businesses
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
