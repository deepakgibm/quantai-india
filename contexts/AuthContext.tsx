import React, { createContext, useContext, useEffect, useState } from 'react';
import {
    onAuthStateChanged,
    User,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    sendPasswordResetEmail,
    GoogleAuthProvider,
    signInWithPopup
} from 'firebase/auth';
import { auth } from '../lib/firebase';
import { api } from '../services/api';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, pass: string) => Promise<any>;
    signup: (email: string, pass: string) => Promise<any>;
    logout: () => Promise<void>;
    resetPassword: typeof sendPasswordResetEmail;
    signInWithGoogle: () => Promise<any>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within an AuthProvider");
    return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
            setUser(currentUser);

            // Sync with backend when Firebase user is detected
            if (currentUser) {
                try {
                    // Check if we already have a valid token
                    const existingToken = localStorage.getItem('access_token');
                    if (!existingToken || existingToken === 'null' || existingToken === 'undefined') {
                        // Fetch a new backend token using Firebase ID token
                        const idToken = await currentUser.getIdToken();
                        await api.firebaseLogin(idToken, currentUser.email!, currentUser.displayName || undefined);
                        console.log('[Auth] Backend token synced successfully');
                    }
                } catch (err) {
                    console.error('[Auth] Failed to sync with backend:', err);
                    // Clear potentially stale token
                    localStorage.removeItem('access_token');
                }
            } else {
                // User logged out - clear token
                localStorage.removeItem('access_token');
            }

            setLoading(false);
        });
        return () => unsubscribe();
    }, []);

    const login = async (email: string, pass: string) => {
        const userCredential = await signInWithEmailAndPassword(auth, email, pass);
        const idToken = await userCredential.user.getIdToken();
        await api.firebaseLogin(idToken, userCredential.user.email!, userCredential.user.displayName || undefined);
        return userCredential;
    };

    const signup = async (email: string, pass: string) => {
        const userCredential = await createUserWithEmailAndPassword(auth, email, pass);
        const idToken = await userCredential.user.getIdToken();
        await api.firebaseLogin(idToken, userCredential.user.email!, userCredential.user.displayName || undefined);
        return userCredential;
    };

    const logout = async () => {
        localStorage.removeItem('access_token');
        await signOut(auth);
    };

    const resetPassword = (email: string) => sendPasswordResetEmail(auth, email);

    const signInWithGoogle = async () => {
        const provider = new GoogleAuthProvider();
        const userCredential = await signInWithPopup(auth, provider);
        const idToken = await userCredential.user.getIdToken();
        await api.firebaseLogin(idToken, userCredential.user.email!, userCredential.user.displayName || undefined);
        return userCredential;
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, signup, logout, resetPassword, signInWithGoogle }}>
            {loading ? (
                <div className="min-h-screen flex items-center justify-center bg-slate-900">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
                </div>
            ) : (
                children
            )}
        </AuthContext.Provider>
    );
};
