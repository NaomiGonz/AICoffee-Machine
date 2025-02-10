import { auth } from "./firebase";
import { createUserWithEmailAndPassword, GoogleAuthProvider, signInWithEmailAndPassword, sendPasswordResetEmail, signInWithPopup } from "firebase/auth";

export const signUp = async (email, password) => {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        return userCredential.user;
    } catch (error) {
        console.error("Error signing up:", error);
        return null;
    }
};

export const signIn = async (email, password) => {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        return userCredential.user;
    } catch (error) {
        console.error("Error signing in:", error);
        return null;
    }
};

export const signInWithGoogle = async () => {
    try {
        const provider = new GoogleAuthProvider();
        const userCredential = await signInWithPopup(auth, provider);
        // TODO: Save userCredential.user to the database like firestore?
        return userCredential;
    } catch (error) {
        console.error("Error signing in with Google:", error);
        return null;
    }
};

export const signOut = async () => {
    try {
        await auth.signOut();
    } catch (error) {
        console.error("Error signing out:", error);
    }
};

export const resetPassword = async (email) => {
    try {
        return sendPasswordResetEmail(auth, email);
    } catch (error) {
        console.error("Error resetting password:", error);
    }
};

export const updatePassword = async (password) => {
    try {
        return updatePassword(auth.currentUser, password);
    } catch (error) {
        console.error("Error updating password:", error);
    }
};

export const emailVerification = async () => {
    try {
        return await sendEmailVerification(auth.currentUser);
    } catch (error) {
        console.error("Error sending email verification:", error);
    }
}