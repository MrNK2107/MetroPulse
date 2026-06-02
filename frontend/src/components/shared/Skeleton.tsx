"use client";

import React from "react";

interface SkeletonProps {
  className?: string;
}

/** Base skeleton pulse element */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-dark-100/40 ${className}`}
      aria-hidden="true"
    />
  );
}

/** Skeleton for a conversation panel (left sidebar) */
export function ConversationPanelSkeleton() {
  return (
    <div className="w-full md:w-[360px] h-full bg-dark-200/95 backdrop-blur-md p-4 space-y-4">
      <Skeleton className="h-6 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="space-y-3 mt-6">
        <Skeleton className="h-10 w-full rounded-xl" />
        <Skeleton className="h-10 w-full rounded-xl" />
        <Skeleton className="h-10 w-5/6 rounded-xl" />
      </div>
      <div className="mt-8 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-2/3" />
      </div>
      <div className="mt-6">
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
    </div>
  );
}

/** Skeleton for the evidence panel (right sidebar) */
export function EvidencePanelSkeleton() {
  return (
    <div className="w-full md:w-[420px] h-full bg-dark-200/95 backdrop-blur-md">
      <div className="border-b border-dark-100/40 p-5 bg-dark-300/40">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-2.5 w-48 mt-2" />
      </div>
      <div className="p-5 space-y-4">
        <div className="flex gap-1">
          <Skeleton className="h-7 flex-1 rounded-lg" />
          <Skeleton className="h-7 flex-1 rounded-lg" />
          <Skeleton className="h-7 flex-1 rounded-lg" />
          <Skeleton className="h-7 flex-1 rounded-lg" />
        </div>
        <Skeleton className="h-4 w-3/4" />
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-4/5" />
        </div>
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-4 w-2/3" />
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/6" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-3/5" />
        </div>
      </div>
    </div>
  );
}
