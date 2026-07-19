import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock the global WebSocket so we can drive frames without a server.
class FakeWebSocket {
  static last: FakeWebSocket | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  sent: string[] = [];
  closed = false;

  constructor(public url: string) {
    FakeWebSocket.last = this;
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.closed = true;
    this.onclose?.();
  }
  // test helper: simulate a server frame
  emit(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
  // test helper: simulate a connection failure
  fail() {
    this.onerror?.();
  }
}

vi.stubGlobal("WebSocket", FakeWebSocket as any);

import { useLiveWorkflow } from "@/lib/useLiveWorkflow";

describe("useLiveWorkflow", () => {
  beforeEach(() => {
    FakeWebSocket.last = null;
  });

  it("connects when a workflow id is provided", () => {
    const onUpdate = vi.fn();
    const { unmount } = renderHook(() => useLiveWorkflow("wf-1", onUpdate));
    expect(FakeWebSocket.last?.url).toContain("/ws/wf-1");
    unmount();
    expect(FakeWebSocket.last?.closed).toBe(true);
  });

  it("forwards parsed frames to onUpdate", () => {
    const onUpdate = vi.fn();
    renderHook(() => useLiveWorkflow("wf-1", onUpdate));
    act(() => {
      FakeWebSocket.last?.emit({ status: "running", progress: 0.4 });
    });
    expect(onUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ status: "running", progress: 0.4 }),
    );
  });

  it("does not connect when workflow id is null", () => {
    const onUpdate = vi.fn();
    renderHook(() => useLiveWorkflow(null, onUpdate));
    expect(FakeWebSocket.last).toBeNull();
  });

  it("calls onClose when the socket errors", () => {
    const onUpdate = vi.fn();
    const onClose = vi.fn();
    renderHook(() => useLiveWorkflow("wf-1", onUpdate, onClose));
    act(() => {
      FakeWebSocket.last?.fail();
    });
    expect(onClose).toHaveBeenCalled();
  });
});
