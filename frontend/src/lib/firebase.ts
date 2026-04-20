import { initializeApp, FirebaseApp } from "firebase/app";
import { getAuth, Auth } from "firebase/auth";

const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "demo-key",
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "demo.firebaseapp.com",
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "demo-project",
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "",
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "",
    appId: import.meta.env.VITE_FIREBASE_APP_ID || ""
};

let app: FirebaseApp;
let auth: Auth;

try {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
} catch (error) {
    console.error("Firebase initialization failed:", error);
    // Create a minimal auth object to prevent crashes
    app = initializeApp(firebaseConfig, "fallback");
    auth = getAuth(app);
}

export { auth };

