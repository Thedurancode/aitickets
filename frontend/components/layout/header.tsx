"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Ticket,
  ShoppingCart,
  Menu,
  X,
  CalendarDays,
  MapPin,
  LogIn,
  UserPlus,
  LayoutDashboard,
  LogOut,
  User,
} from "lucide-react";
import { useCheckoutStore } from "@/stores/checkout-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { auth } from "@/lib/auth";

export function Header() {
  const { selectedTier, quantity } = useCheckoutStore();
  const hasItemsInCart = selectedTier !== null;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      if (auth.isLoggedIn()) {
        setLoggedIn(true);
        try {
          const user = await auth.getUser();
          setUserName(user.name);
          setAvatarUrl(user.avatar_url || null);
        } catch {
          // Token may be expired
          setLoggedIn(false);
        }
      }
    };
    checkAuth();
  }, []);

  const handleLogout = () => {
    auth.logout();
    setLoggedIn(false);
    setUserName(null);
    setAvatarUrl(null);
    setMobileMenuOpen(false);
    router.push("/events");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-background/80 backdrop-blur-xl">
      <div className="container px-4 sm:px-6 lg:px-8 flex h-14 sm:h-16 items-center justify-between">
        <Link href="/events" className="flex items-center gap-2 group">
          <motion.div
            whileHover={{ rotate: 15, scale: 1.1 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="p-1.5 sm:p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors"
          >
            <Ticket className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
          </motion.div>
          <span className="font-bold text-lg sm:text-xl text-foreground">Tickets</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden sm:flex items-center gap-2">
          <Link href="/events">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              Events
            </Button>
          </Link>

          <Link href="/venues">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              Venues
            </Button>
          </Link>

          <Link href="/tickets">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              My Tickets
            </Button>
          </Link>

          <Link href="/checkout" className="relative">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                variant={hasItemsInCart ? "default" : "outline"}
                size="sm"
                className={hasItemsInCart ? "glow-sm" : ""}
              >
                <ShoppingCart className="h-4 w-4 mr-2" />
                Cart
                {hasItemsInCart && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute -top-2 -right-2"
                  >
                    <Badge className="h-5 w-5 p-0 flex items-center justify-center text-xs bg-primary text-primary-foreground">
                      {quantity}
                    </Badge>
                  </motion.div>
                )}
              </Button>
            </motion.div>
          </Link>

          {/* Auth section */}
          {loggedIn ? (
            <>
              <Link href="/dashboard">
                <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground gap-2">
                  {avatarUrl ? (
                    <img src={avatarUrl} alt="" className="h-5 w-5 rounded-full object-cover" />
                  ) : (
                    <User className="h-4 w-4" />
                  )}
                  {userName || "Dashboard"}
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-red-400"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                  <LogIn className="h-4 w-4 mr-2" />
                  Login
                </Button>
              </Link>
              <Link href="/register">
                <Button variant="outline" size="sm" className="border-white/10">
                  <UserPlus className="h-4 w-4 mr-2" />
                  Sign Up
                </Button>
              </Link>
            </>
          )}
        </nav>

        {/* Mobile: cart + hamburger */}
        <div className="flex sm:hidden items-center gap-2">
          <Link href="/checkout" className="relative">
            <Button
              variant={hasItemsInCart ? "default" : "ghost"}
              size="icon"
              className="h-10 w-10"
            >
              <ShoppingCart className="h-4 w-4" />
              {hasItemsInCart && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-1 -right-1"
                >
                  <Badge className="h-4 w-4 p-0 flex items-center justify-center text-[10px] bg-primary text-primary-foreground">
                    {quantity}
                  </Badge>
                </motion.div>
              )}
            </Button>
          </Link>

          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="sm:hidden border-t border-white/5 bg-background/95 backdrop-blur-xl overflow-hidden"
          >
            <nav className="container px-4 py-3 flex flex-col gap-1">
              <Link
                href="/events"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
              >
                <CalendarDays className="h-4 w-4 text-muted-foreground" />
                Events
              </Link>
              <Link
                href="/venues"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
              >
                <MapPin className="h-4 w-4 text-muted-foreground" />
                Venues
              </Link>
              <Link
                href="/tickets"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
              >
                <Ticket className="h-4 w-4 text-muted-foreground" />
                My Tickets
              </Link>
              <Link
                href="/checkout"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
              >
                <ShoppingCart className="h-4 w-4 text-muted-foreground" />
                Cart {hasItemsInCart && `(${quantity})`}
              </Link>

              <div className="border-t border-white/5 my-2" />

              {loggedIn ? (
                <>
                  <Link
                    href="/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
                  >
                    <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
                    Dashboard
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-3 py-3 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors w-full text-left"
                  >
                    <LogOut className="h-4 w-4" />
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
                  >
                    <LogIn className="h-4 w-4 text-muted-foreground" />
                    Login
                  </Link>
                  <Link
                    href="/register"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center gap-3 px-3 py-3 rounded-lg text-foreground hover:bg-white/5 transition-colors"
                  >
                    <UserPlus className="h-4 w-4 text-muted-foreground" />
                    Sign Up
                  </Link>
                </>
              )}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
