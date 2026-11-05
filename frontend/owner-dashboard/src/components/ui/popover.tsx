import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/utils";

/** Minimal click-outside / Escape dismissable dropdown. */
export function Popover({
  trigger,
  children,
  align = "right",
  panelClassName,
  onOpenChange,
}: {
  trigger: (props: {
    open: boolean;
    toggle: () => void;
    close: () => void;
  }) => ReactNode;
  children: (props: { close: () => void }) => ReactNode;
  align?: "left" | "right";
  panelClassName?: string;
  onOpenChange?: (open: boolean) => void;
}) {
  const [open, setOpenState] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const setOpen = (next: boolean) => {
    setOpenState(next);
    onOpenChange?.(next);
  };

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpenState(false);
        onOpenChange?.(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenState(false);
        onOpenChange?.(false);
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onOpenChange]);

  return (
    <div ref={ref} className="relative">
      {trigger({
        open,
        toggle: () => setOpen(!open),
        close: () => setOpen(false),
      })}
      {open ? (
        <div
          className={cn(
            "absolute z-40 mt-2 rounded-xl border border-border bg-surface text-foreground shadow-lg transition-colors",
            align === "right" ? "right-0" : "left-0",
            panelClassName,
          )}
        >
          {children({ close: () => setOpen(false) })}
        </div>
      ) : null}
    </div>
  );
}
