"use client";
import { notFound, useParams } from "next/navigation";
import { VIEWS } from "@/components/views";

export default function ViewPage() {
  const { role, view } = useParams<{ role: string; view: string }>();
  const Component = VIEWS[role]?.[view];
  if (!Component) notFound();
  return <Component />;
}
