"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  MessageSquare, FileText, Settings, Shield, Plus, Trash2,
  ChevronLeft, ChevronRight, Sun, Moon, LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useThemeStore } from "@/stores/theme-store";
import { useChatStore } from "@/stores/chat-store";
import { useConversations, useDeleteConversation } from "@/hooks/use-conversations";

const navItems = [
  { href: "/", icon: MessageSquare, label: "Chat" },
  { href: "/documents", icon: FileText, label: "Documents" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { theme, toggle } = useThemeStore();
  const { clearChat } = useChatStore();
  const { data: convData } = useConversations();
  const deleteMutation = useDeleteConversation();

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 280 }}
      className="h-screen border-r bg-card flex flex-col"
    >
      <div className="p-4 flex items-center justify-between border-b">
        {!collapsed && <span className="font-bold text-lg">DocMind</span>}
        <Button variant="ghost" size="icon" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      <div className="p-2">
        <Button
          className="w-full justify-start gap-2"
          variant="outline"
          onClick={clearChat}
          asChild
        >
          <Link href="/">
            <Plus className="h-4 w-4" />
            {!collapsed && "New Chat"}
          </Link>
        </Button>
      </div>

      <nav className="px-2 space-y-1">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href}>
            <div
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent",
                pathname === item.href && "bg-accent text-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && item.label}
            </div>
          </Link>
        ))}
        {user?.role === "admin" && (
          <Link href="/admin">
            <div
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent",
                pathname === "/admin" && "bg-accent text-accent-foreground"
              )}
            >
              <Shield className="h-4 w-4 shrink-0" />
              {!collapsed && "Admin"}
            </div>
          </Link>
        )}
      </nav>

      {!collapsed && (
        <div className="flex-1 overflow-hidden mt-4">
          <div className="px-3 mb-2 text-xs font-medium text-muted-foreground">Recent Chats</div>
          <ScrollArea className="h-[calc(100vh-380px)]">
            <div className="px-2 space-y-1">
              {convData?.conversations?.map((conv) => (
                <div
                  key={conv.id}
                  className="group flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-accent cursor-pointer"
                >
                  <Link href={`/?c=${conv.id}`} className="flex-1 truncate">
                    {conv.title}
                  </Link>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      deleteMutation.mutate(conv.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label={`Delete conversation: ${conv.title}`}
                  >
                    <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                  </button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      <div className="mt-auto border-t p-3 space-y-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
            {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </Button>
          {!collapsed && (
            <span className="text-xs text-muted-foreground truncate">{user?.email}</span>
          )}
          <Button variant="ghost" size="icon" onClick={logout} className="ml-auto" aria-label="Logout">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </motion.aside>
  );
}
