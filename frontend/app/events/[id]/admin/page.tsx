import type { Metadata } from "next";
import AdminContent from "./admin-content";

export const metadata: Metadata = {
  title: "Event Admin",
  robots: { index: false, follow: false },
};

export default function EventAdminPage() {
  return <AdminContent />;
}
