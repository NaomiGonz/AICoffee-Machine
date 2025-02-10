import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyD4ynX4PMihe31U1FA3NM50QfERD1QSOFY",
    authDomain: "ai-coffee-a5ad7.firebaseapp.com",
    projectId: "ai-coffee-a5ad7",
    storageBucket: "ai-coffee-a5ad7.firebasestorage.app",
    messagingSenderId: "69058188119",
    appId: "1:69058188119:web:e46951a7ba1919d95de412",
    measurementId: "G-1L3RE5DBGV"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export { app, auth };