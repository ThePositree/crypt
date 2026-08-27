import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocPage, metadataForDoc } from "@/components/doc-page";
import { docs } from "@/lib/docs";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return docs.map((doc) => ({ slug: doc.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;

  if (!docs.some((doc) => doc.slug === slug)) {
    return {};
  }

  return metadataForDoc(slug);
}

export default async function DynamicDocPage({ params }: PageProps) {
  const { slug } = await params;

  if (!docs.some((doc) => doc.slug === slug)) {
    notFound();
  }

  return <DocPage slug={slug} />;
}
