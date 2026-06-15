import { initializeApp, getApps } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || (window as any)._VIT_CONFIG?.platform?.firebase?.apiKey,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || (window as any)._VIT_CONFIG?.platform?.firebase?.authDomain,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || (window as any)._VIT_CONFIG?.platform?.firebase?.projectId,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || (window as any)._VIT_CONFIG?.platform?.firebase?.storageBucket,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || (window as any)._VIT_CONFIG?.platform?.firebase?.messagingSenderId,
  appId: import.meta.env.VITE_FIREBASE_APP_ID || (window as any)._VIT_CONFIG?.platform?.firebase?.appId,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || (window as any)._VIT_CONFIG?.platform?.firebase?.measurementId,
};

// F1: Fix Firebase TS robustness and credential detection
const isFirebaseConfigured = !!(
  firebaseConfig.apiKey &&
  firebaseConfig.apiKey.length > 10 &&
  firebaseConfig.authDomain &&
  firebaseConfig.projectId
);

let app: ReturnType<typeof initializeApp> | null = null;
let analytics: any = null;

if (isFirebaseConfigured) {
  try {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
    if (typeof window !== "undefined") {
      import("firebase/analytics").then(({ getAnalytics }) => {
        try {
          analytics = getAnalytics(app!);
        } catch (e) {
          console.warn("Firebase Analytics initialization failed:", e);
        }
      }).catch(() => {});
    }
  } catch (e) {
    console.error("Firebase initialization failed. Configuration may be invalid.", e);
    app = null;
  }
}

export const auth = isFirebaseConfigured && app ? getAuth(app) : null;

// Helper to check if Firebase is fully operational
export const isFirebaseReady = () => isFirebaseConfigured && !!app;
export const googleProvider = new GoogleAuthProvider();
export const db = isFirebaseConfigured && app ? getFirestore(app) : null;
export { analytics };
export { isFirebaseConfigured };
export default app;

export const getDynamicAuth = () => {
  if (auth) return auth;
  if (isFirebaseReady() && app) return getAuth(app);
  return null;
};
