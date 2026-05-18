import { initializeApp, getApps } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

const isFirebaseConfigured = !!(
  firebaseConfig.apiKey &&
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
    console.warn("Firebase initialization failed:", e);
    app = null;
  }
}

export const auth = isFirebaseConfigured && app ? getAuth(app) : null;
export const googleProvider = isFirebaseConfigured ? new GoogleAuthProvider() : null;
export const db = isFirebaseConfigured && app ? getFirestore(app) : null;
export { analytics };
export { isFirebaseConfigured };
export default app;
