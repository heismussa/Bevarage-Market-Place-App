import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon,
  footer,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  footer?: ReactNode;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted">{label}</p>
        {icon ? (
          <div
            className={cn(
              "rounded-xl p-2",
              tone === "default" && "bg-primary-soft text-primary",
              tone === "warning" && "bg-warning-soft text-warning",
              tone === "danger" && "bg-danger-soft text-danger",
            )}
          >
            {icon}
          </div>
        ) : null}
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight">{value}</p>
      {footer ? <div className="mt-2 min-h-5">{footer}</div> : null}
    </Card>
  );
}
