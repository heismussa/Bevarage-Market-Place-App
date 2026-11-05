import { ImagePlus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

/** Returns an error message, or null when the file is acceptable. */
function validateImage(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return "Use a JPEG, PNG or WebP image.";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return "Image must be under 2 MB.";
  }
  return null;
}

export function ImagePicker({
  currentUrl,
  file,
  onFileChange,
  label = "Image",
  shape = "square",
}: {
  currentUrl?: string | null;
  file: File | null;
  onFileChange: (file: File | null) => void;
  label?: string;
  shape?: "square" | "round";
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const shown = preview ?? currentUrl ?? null;

  return (
    <div>
      <p className="mb-1.5 text-sm font-medium">{label}</p>
      <div className="flex items-center gap-4">
        <div
          className={`flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden border border-border bg-surface-muted text-muted ${
            shape === "round" ? "rounded-full" : "rounded-xl"
          }`}
        >
          {shown ? (
            <img src={shown} alt="" className="h-full w-full object-cover" />
          ) : (
            <ImagePlus size={24} />
          )}
        </div>
        <div className="space-y-1">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => inputRef.current?.click()}
            >
              {shown ? "Change" : "Upload"}
            </Button>
            {file ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setError(null);
                  onFileChange(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
              >
                <X size={14} /> Remove new
              </Button>
            ) : null}
          </div>
          <p className="text-xs text-muted">JPEG, PNG or WebP, under 2 MB.</p>
          {error ? (
            <p role="alert" className="text-xs text-danger">
              {error}
            </p>
          ) : null}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_TYPES.join(",")}
          className="hidden"
          onChange={(event) => {
            const picked = event.target.files?.[0] ?? null;
            if (!picked) return;
            const problem = validateImage(picked);
            if (problem) {
              setError(problem);
              event.target.value = "";
              return;
            }
            setError(null);
            onFileChange(picked);
          }}
        />
      </div>
    </div>
  );
}
