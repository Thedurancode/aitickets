"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Image as ImageIcon, Loader2, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAdminUploadImage } from "@/lib/queries";

interface ImageUploadProps {
  currentImageUrl: string | null;
  eventId: number;
  token: string;
}

export function ImageUpload({
  currentImageUrl,
  eventId,
  token,
}: ImageUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const uploadMutation = useAdminUploadImage(eventId, token);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      uploadMutation.mutate(file);
    },
    [uploadMutation]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-lg">Event Image</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {currentImageUrl && (
          <div className="relative aspect-video rounded-lg overflow-hidden border border-white/5">
            <img
              src={currentImageUrl}
              alt="Current event image"
              className="w-full h-full object-cover"
            />
          </div>
        )}

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragOver
              ? "border-primary bg-primary/5"
              : "border-white/10 hover:border-white/20"
          }`}
        >
          {uploadMutation.isPending ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Uploading...</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col items-center gap-2">
                <div className="p-3 rounded-full bg-primary/10">
                  <Upload className="h-6 w-6 text-primary" />
                </div>
                <p className="text-sm text-foreground font-medium">
                  Drag & drop an image here
                </p>
                <p className="text-xs text-muted-foreground">
                  or click to browse
                </p>
              </div>
              <input
                type="file"
                accept="image/*"
                onChange={onFileSelect}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </>
          )}
        </div>

        {uploadMutation.isSuccess && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-green-400 text-center"
          >
            Image uploaded successfully
          </motion.p>
        )}

        {uploadMutation.isError && (
          <p className="text-sm text-red-400 text-center">
            Upload failed. Please try again.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
