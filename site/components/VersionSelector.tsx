"use client";

import { ChevronDown } from "lucide-react";
import { currentVersion, versions } from "@/lib/content";

export function VersionSelector() {
  return (
    <label className="version-select">
      <span className="sr-only">Docs version</span>
      <select defaultValue={currentVersion} aria-label="Docs version">
        {versions.map((version) => (
          <option key={version} value={version}>
            {version}
          </option>
        ))}
      </select>
      <ChevronDown size={16} aria-hidden="true" />
    </label>
  );
}
