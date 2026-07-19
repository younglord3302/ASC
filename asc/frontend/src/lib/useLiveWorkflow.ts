"use client";

// Live workflow updates over WebSocket, with graceful polling fallback.
//
// The backend exposes `/ws/{workflow_id}` (see app/api/routes.py). When the
// socket is available we stream status/progress/messages in real time;
// if it fails to open we signal the caller so it can fall back to polling.

import { useEffect } from "react";
import { wsUrl } from "@/lib/auth";

interface LiveUpdate {
  status?: string;
  progress?: number;
  current_agent?: string | null;
  messages?: Array<{
    id: string;
    from: string;
    to?: string | null;
    type: string;
    content: string;
    timestamp: string;
  }>;
}

/**
 * Open a WebSocket to the given workflow and forward updates to `onUpdate`.
 * `onClose` fires if the socket errors/closes so the caller can poll instead.
 * Pass `null` to disconnect.
 */
export function useLiveWorkflow(
  workflowId: string | null,
  onUpdate: (update: LiveUpdate) => void,
  onClose?: () => void,
) {
  useEffect(() => {
    if (!workflowId) return;

    let socket: WebSocket | null = null;
    let cancelled = false;
    let retry: any = null;

    const connect = () => {
      if (cancelled) return;
      try {
        socket = new WebSocket(wsUrl(`/ws/${workflowId}`));
      } catch {
        onClose?.();
        return;
      }

      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          onUpdate(JSON.parse(event.data) as LiveUpdate);
        } catch {
          /* ignore malformed frames */
        }
      };

      socket.onerror = () => {
        if (!cancelled) onClose?.();
      };

      socket.onclose = () => {
        if (!cancelled) onClose?.();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.onmessage = null;
        try {
          socket.close();
        } catch {
          /* ignore */
        }
      }
    };
  }, [workflowId, onUpdate, onClose]);
}
