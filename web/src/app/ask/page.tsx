import type { Metadata } from "next";
import AskClient from "./AskClient";

export const metadata: Metadata = {
  title: "Ask | CampusAsk | UCM",
  description: "Grounded UCM catalog Q&A with citations and safe abstention.",
};

export default function AskPage() {
  return <AskClient />;
}
