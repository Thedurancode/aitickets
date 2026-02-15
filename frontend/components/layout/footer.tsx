import Link from "next/link";
import { Ticket } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-white/5 bg-background/50">
      <div className="container py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 rounded-lg bg-primary/10">
                <Ticket className="h-4 w-4 text-primary" />
              </div>
              <span className="font-bold text-foreground">Tickets</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Your trusted platform for discovering and purchasing tickets to
              amazing events.
            </p>
          </div>

          <div>
            <h3 className="font-semibold mb-4 text-sm uppercase tracking-wider text-muted-foreground">Quick Links</h3>
            <ul className="space-y-3 text-sm">
              <li>
                <Link
                  href="/events"
                  className="text-muted-foreground hover:text-primary transition-colors"
                >
                  Browse Events
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-4 text-sm uppercase tracking-wider text-muted-foreground">Contact</h3>
            <p className="text-sm text-muted-foreground">
              Need help? Contact our support team.
            </p>
          </div>
        </div>

        <div className="border-t border-white/5 mt-12 pt-8 text-center text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} Tickets. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
