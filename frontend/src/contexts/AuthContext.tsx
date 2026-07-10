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
        let isMounted = true;

        const checkExistingAuth = async (): Promise<boolean> => {
            const token = localStorage.getItem('access_token');
            if (token && token !== 'null' && token !== 'undefined') {
                try {
                    const profile = await api.getCurrentUser();
                    if (profile && isMounted) {
                        setUser({
                            uid: String(profile.id),
                            email: profile.email,
                            displayName: profile.full_name || profile.username,
                            emailVerified: true,
                        } as any);
                        return true;
                    }
                } catch (e) {
                    console.warn("[Auth] Failed to restore session from existing token:", e);
                }
            }
            return false;
        };

        const unsubscribe = onIdTokenChanged(auth, async (currentUser) => {
            if (currentUser) {
                try {
                    const idToken = await currentUser.getIdToken(true);
                    const syncResult = await api.firebaseLogin(idToken, currentUser.email!, currentUser.displayName || undefined);
                    if (syncResult && syncResult.access_token) {
                        console.log('[Auth] Backend token successfully refreshed and synced');
                        if (isMounted) setUser(currentUser);
                    } else {
                        console.warn('[Auth] Sync returned no token, clearing legacy state');
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        if (isMounted) setUser(null);
                    }
                } catch (err: any) {
                    console.error('[Auth] Sync failure:', err);
                    const isAuthError = err.message?.includes('401') || err.message?.includes('403') || err.message?.includes('Unauthorized');
                    if (isAuthError) {
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        if (isMounted) setUser(null);
                    } else {
                        const restored = await checkExistingAuth();
                        if (!restored && isMounted) {
                            setUser(null);
                        }
                    }
                }
            } else {
                const restored = await checkExistingAuth();
                if (!restored && isMounted) {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    setUser(null);
                }
            }
            if (isMounted) setLoading(false);
        });

        // Run initial check on mount
        checkExistingAuth().then((restored) => {
            if (restored && isMounted) {
                setLoading(false);
            }
        });

        return () => {
            isMounted = false;
            unsubscribe();
        };
    }, []);

    const login = async (email: string, pass: string) => {
        try {
            console.log("[Auth] Attempting Firebase login...");
            const userCredential = await signInWithEmailAndPassword(auth, email, pass);
            const idToken = await userCredential.user.getIdToken();
            await api.firebaseLogin(idToken, userCredential.user.email!, userCredential.user.displayName || undefined);
            return userCredential;
        } catch (firebaseErr: any) {
            console.warn("[Auth] Firebase login failed, falling back to direct backend login:", firebaseErr);
            const result = await api.login(email, pass);
            if (result && result.access_token) {
                const profile = await api.getCurrentUser();
                const mockUser = {
                    uid: String(profile?.id || 1),
                    email: email,
                    displayName: profile?.full_name || profile?.username || "User",
                    emailVerified: true,
                } as any;
                setUser(mockUser);
                return { user: mockUser };
            }
            throw firebaseErr;
        }
    };

    const signup = async (email: string, pass: string) => {
        try {
            console.log("[Auth] Attempting Firebase signup...");
            const userCredential = await createUserWithEmailAndPassword(auth, email, pass);
            const idToken = await userCredential.user.getIdToken();
            await api.firebaseLogin(idToken, userCredential.user.email!, userCredential.user.displayName || undefined);
            return userCredential;
        } catch (firebaseErr: any) {
            console.warn("[Auth] Firebase signup failed, falling back to direct backend signup:", firebaseErr);
            const result = await api.signup(email, pass, email.split('@')[0], "User");
            if (result && result.access_token) {
                const profile = await api.getCurrentUser();
                const mockUser = {
                    uid: String(profile?.id || 1),
                    email: email,
                    displayName: profile?.full_name || profile?.username || "User",
                    emailVerified: true,
                } as any;
                setUser(mockUser);
                return { user: mockUser };
            }
            throw firebaseErr;
        }
    };

    const logout = async () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
        try {
            await signOut(auth);
        } catch (e) {
            console.warn("Firebase signout failed:", e);
        }
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
