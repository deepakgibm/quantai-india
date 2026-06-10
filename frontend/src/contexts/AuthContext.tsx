import React, { createContext, useContext, useEffect, useState } from 'react';
import {
    onIdTokenChanged,
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
        const unsubscribe = onIdTokenChanged(auth, async (currentUser) => {
            if (currentUser) {
                try {
                    // CRITICAL: Always verify or refresh the backend token to prevent 401s
                    const idToken = await currentUser.getIdToken(true); // true = force refresh

                    // Sync with backend to get a fresh local JWT
                    const syncResult = await api.firebaseLogin(idToken, currentUser.email!, currentUser.displayName || undefined);

                    if (syncResult && syncResult.access_token) {
                        console.log('[Auth] Backend token successfully refreshed and synced');
                        setUser(currentUser);
                    } else {
                        console.warn('[Auth] Sync returned no token, clearing legacy state');
                        localStorage.removeItem('access_token');
                        setUser(null);
                    }
                } catch (err: any) {
                    console.error('[Auth] Sync failure:', err);

                    // IMPORTANT: Only clear token if it's a definitive auth failure (401/403)
                    // Do NOT clear on network errors (fetch failure) as the backend might just be restarting
                    const isAuthError = err.message?.includes('401') || err.message?.includes('403') || err.message?.includes('Unauthorized');
                    if (isAuthError) {
                        console.warn('[Auth] Definitive auth failure, clearing token');
                        localStorage.removeItem('access_token');
                        setUser(null);
                    } else {
                        console.warn('[Auth] Non-auth failure (network?), retaining existing token');
                        const existingToken = localStorage.getItem('access_token');
                        if (existingToken) {
                            setUser(currentUser);
                        } else {
                            setUser(null);
                        }
                    }
                }
            } else {
                localStorage.removeItem('access_token');
                setUser(null);
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
