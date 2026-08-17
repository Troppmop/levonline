import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    output[i] = rawData.charCodeAt(i);
  }
  return output;
}

export type PushSupportState = "unsupported" | "subscribed" | "unsubscribed";

export function usePushNotifications() {
  const [state, setState] = useState<PushSupportState>("unsubscribed");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supported = "serviceWorker" in navigator && "PushManager" in window;

  const refresh = useCallback(async () => {
    if (!supported) {
      setState("unsupported");
      return;
    }
    const registration = await navigator.serviceWorker.ready;
    const existing = await registration.pushManager.getSubscription();
    setState(existing ? "subscribed" : "unsubscribed");
  }, [supported]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const enable = useCallback(async () => {
    if (!supported) return;
    setLoading(true);
    setError(null);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setError("Notification permission was not granted");
        return;
      }
      const { public_key } = await api.get<{ public_key: string }>("/push/vapid-public-key");
      if (!public_key) {
        setError("Push notifications aren't configured on the server yet");
        return;
      }
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });
      await api.post("/push/subscribe", subscription.toJSON());
      setState("subscribed");
    } catch {
      setError("Could not enable push notifications");
    } finally {
      setLoading(false);
    }
  }, [supported]);

  const disable = useCallback(async () => {
    if (!supported) return;
    setLoading(true);
    setError(null);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await api.delete("/push/unsubscribe", { endpoint: subscription.endpoint });
        await subscription.unsubscribe();
      }
      setState("unsubscribed");
    } catch {
      setError("Could not disable push notifications");
    } finally {
      setLoading(false);
    }
  }, [supported]);

  return { state, supported, loading, error, enable, disable };
}
