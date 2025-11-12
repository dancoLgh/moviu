export async function registerPush() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  const registration = await navigator.serviceWorker.register('/sw.js');
  return registration;
}

export async function subscribeToPush(registration: ServiceWorkerRegistration, vapidKey: string) {
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: vapidKey
  });
  return subscription.toJSON();
}
