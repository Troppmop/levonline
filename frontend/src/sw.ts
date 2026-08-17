/// <reference lib="webworker" />
import { clientsClaim } from "workbox-core";
import { precacheAndRoute } from "workbox-precaching";

declare const self: ServiceWorkerGlobalScope;

// injectManifest strategy (rather than generateSW): we need this file to
// author custom `push`/`notificationclick` listeners below, which
// generateSW's auto-generated worker has no hook for. No `fetch` listener
// is added here, so requests fall through to the network untouched —
// same "never cache API/uploads responses" behavior the old generateSW
// runtimeCaching config had, just for free instead of configured.
precacheAndRoute(self.__WB_MANIFEST);

// generateSW auto-adds these when registerType is "autoUpdate"; a
// hand-authored injectManifest worker like this one has to do it itself,
// or a newly deployed SW sits "waiting" until every open tab is fully
// closed (not just refreshed) before it ever takes over — deployed
// changes would otherwise appear to not exist for anyone with the app
// already open.
self.skipWaiting();
clientsClaim();

self.addEventListener("push", (event: PushEvent) => {
  if (!event.data) return;
  let payload: { title?: string; body?: string; url?: string };
  try {
    payload = event.data.json();
  } catch {
    payload = { title: "Lev LaChayal", body: event.data.text() };
  }

  event.waitUntil(
    self.registration.showNotification(payload.title || "Lev LaChayal", {
      body: payload.body || "",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: payload.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();
  const url = (event.notification.data?.url as string) || "/";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client && new URL(client.url).pathname === url) {
          return (client as WindowClient).focus();
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
