import { formatDateTime } from "@beverage/api";
import { Bell, CheckCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { EmptyState, ErrorState } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Popover } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMarkAllRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from "@/lib/queries";
import { cn } from "@/lib/utils";

export function NotificationsMenu() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const unread = useUnreadCount();
  const list = useNotifications(open);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllRead();

  const count = unread.data ?? 0;

  return (
    <Popover
      onOpenChange={setOpen}
      panelClassName="w-96 max-w-[calc(100vw-1.5rem)]"
      trigger={({ toggle }) => (
        <button
          type="button"
          onClick={toggle}
          aria-label={count > 0 ? `Notifications, ${count} unread` : "Notifications"}
          className="relative rounded-xl p-2 text-foreground hover:bg-surface-muted"
        >
          <Bell size={20} />
          {count > 0 ? (
            <span className="absolute top-0.5 right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
              {count > 99 ? "99+" : count}
            </span>
          ) : null}
        </button>
      )}
    >
      {({ close }) => (
        <div>
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <p className="font-semibold">Notifications</p>
            <Button
              variant="ghost"
              size="sm"
              disabled={count === 0 || markAll.isPending}
              onClick={() => markAll.mutate()}
            >
              <CheckCheck size={14} /> Mark all read
            </Button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {list.isLoading ? (
              <div className="space-y-2 p-4">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : list.isError ? (
              <ErrorState error={list.error} onRetry={() => void list.refetch()} />
            ) : list.data && list.data.results.length > 0 ? (
              <ul>
                {list.data.results.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={cn(
                        "flex w-full gap-3 border-b border-border px-4 py-3 text-left last:border-0 hover:bg-surface-muted",
                        !item.is_read && "bg-primary-soft/50",
                      )}
                      onClick={() => {
                        if (!item.is_read) markRead.mutate(item.id);
                        if (item.order) {
                          close();
                          navigate(`/orders/${item.order}`);
                        }
                      }}
                    >
                      <span
                        className={cn(
                          "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                          item.is_read ? "bg-transparent" : "bg-primary",
                        )}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium">{item.title}</span>
                        <span className="block text-sm text-muted">{item.message}</span>
                        <span className="mt-1 block text-xs text-muted">
                          {formatDateTime(item.created_at)}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No notifications yet" description="New orders and low-stock alerts show up here." />
            )}
          </div>
        </div>
      )}
    </Popover>
  );
}
