import { useState } from "react";
import { auth } from "./firebase";
import { Users, Mail, Lock, User, ArrowRight, ShieldCheck } from "lucide-react";
import './App.css';

import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updateProfile,
    sendPasswordResetEmail
} from "firebase/auth";

function Login({ onLogin }) {
    const [isLogin, setIsLogin] = useState(true);
    const [isForgotPassword, setIsForgotPassword] = useState(false);
    const [formData, setFormData] = useState({
        email: "",
        password: "",
        confirmPassword: "",
        name: "",
    });
    const [message, setMessage] = useState("");
    const [messageType, setMessageType] = useState("error"); // 'error' or 'success'

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async () => {
        setMessage("");
        try {
            if (isLogin) {
                const userCredential = await signInWithEmailAndPassword(
                    auth,
                    formData.email,
                    formData.password
                );
                onLogin({
                    id: userCredential.user.uid,
                    username: userCredential.user.displayName || userCredential.user.email,
                });
            } else {
                if (formData.password !== formData.confirmPassword) {
                    setMessageType("error");
                    setMessage("Passwords do not match");
                    return;
                }
                const userCredential = await createUserWithEmailAndPassword(
                    auth,
                    formData.email,
                    formData.password
                );
                await updateProfile(userCredential.user, {
                    displayName: formData.name,
                });
                onLogin({
                    id: userCredential.user.uid,
                    username: formData.name,
                });
            }
        } catch (error) {
            console.error(error);
            setMessageType("error");
            if (isLogin) {
                setMessage("Invalid email or password.");
            } else {
                setMessage("Signup failed. Please try again.");
            }
        }
    };

    const handleForgotPassword = async () => {
        setMessage("");
        if (!formData.email) {
            setMessageType("error");
            setMessage("Please enter your email address.");
            return;
        }
        try {
            await sendPasswordResetEmail(auth, formData.email);
            setMessageType("success");
            setMessage("A password reset link has been sent to your email.");
        } catch (error) {
            console.error(error);
            setMessageType("error");
            setMessage("Failed to send reset email. Please try again.");
        }
    };

    const toggleMode = () => {
        setIsLogin(!isLogin);
        setIsForgotPassword(false);
        setMessage("");
        setFormData({ email: "", password: "", confirmPassword: "", name: "" });
    };

    const toggleForgotPassword = () => {
        setIsForgotPassword(!isForgotPassword);
        setMessage("");
        setFormData({ ...formData, password: "", confirmPassword: "", name: "" });
    };

    return (
        <div className="global-bg-gradient min-h-screen flex items-center justify-center p-6 font-sans">
            <div className="card-glass rounded-[40px] shadow-2xl p-10 w-full max-w-lg relative overflow-hidden border border-white/10">
                {/* Decorative Elements */}
                <div className="absolute -top-24 -left-24 w-64 h-64 bg-purple-600/20 rounded-full blur-3xl"></div>
                <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-blue-600/20 rounded-full blur-3xl"></div>

                <div className="relative z-10">
                    <div className="text-center mb-10">
                        <div className="inline-flex items-center justify-center p-4 bg-gradient-to-br from-purple-500 to-blue-500 rounded-3xl shadow-xl mb-6 transform hover:rotate-12 transition-transform duration-500">
                            <ShieldCheck className="w-10 h-10 text-white" />
                        </div>
                        <h1 className="text-5xl font-black text-white mb-2 tracking-tighter">SafeChat</h1>
                        <p className="text-purple-200/60 font-bold uppercase tracking-[0.2em] text-xs">Secure Communication System</p>
                    </div>

                    <div className="space-y-6">
                        {isForgotPassword ? (
                            <div className="animate-fade-in space-y-6">
                                <div>
                                    <label className="block text-[10px] font-black text-purple-300 uppercase tracking-widest mb-2 ml-1">Email</label>
                                    <div className="relative group">
                                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-purple-400/40 group-focus-within:text-purple-400 transition-colors" />
                                        <input
                                            type="email"
                                            name="email"
                                            value={formData.email}
                                            onChange={handleChange}
                                            className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                                            placeholder="Email"
                                        />
                                    </div>
                                </div>

                                {message && (
                                    <div className={`p-4 rounded-xl text-xs font-bold text-center ${messageType === "success" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                                        {message}
                                    </div>
                                )}

                                <button
                                    onClick={handleForgotPassword}
                                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-5 rounded-2xl font-black uppercase tracking-[0.2em] text-xs hover:from-purple-700 hover:to-blue-700 transition-all shadow-xl group"
                                >
                                    <span className="flex items-center justify-center">
                                        Request Link <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                                    </span>
                                </button>

                                <button onClick={toggleForgotPassword} className="w-full text-purple-300/60 text-xs font-black uppercase tracking-widest hover:text-white transition-colors">
                                    Return to Login
                                </button>
                            </div>
                        ) : (
                            <div className="animate-fade-in space-y-6">
                                {!isLogin && (
                                    <div>
                                        <label className="block text-[10px] font-black text-purple-300 uppercase tracking-widest mb-2 ml-1">Name</label>
                                        <div className="relative group">
                                            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-purple-400/40 group-focus-within:text-purple-400 transition-colors" />
                                            <input
                                                type="text"
                                                name="name"
                                                value={formData.name}
                                                onChange={handleChange}
                                                className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                                                placeholder="Name"
                                            />
                                        </div>
                                    </div>
                                )}

                                <div>
                                    <label className="block text-[10px] font-black text-purple-300 uppercase tracking-widest mb-2 ml-1">Email</label>
                                    <div className="relative group">
                                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-purple-400/40 group-focus-within:text-purple-400 transition-colors" />
                                        <input
                                            type="email"
                                            name="email"
                                            value={formData.email}
                                            onChange={handleChange}
                                            className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                                            placeholder="Email"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-[10px] font-black text-purple-300 uppercase tracking-widest mb-2 ml-1">Password</label>
                                    <div className="relative group">
                                        <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-purple-400/40 group-focus-within:text-purple-400 transition-colors" />
                                        <input
                                            type="password"
                                            name="password"
                                            value={formData.password}
                                            onChange={handleChange}
                                            className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                                            placeholder="Password"
                                        />
                                    </div>
                                </div>

                                {!isLogin && (
                                    <div>
                                        <label className="block text-[10px] font-black text-purple-300 uppercase tracking-widest mb-2 ml-1">Re-verify Key</label>
                                        <div className="relative group">
                                            <ShieldCheck className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-purple-400/40 group-focus-within:text-purple-400 transition-colors" />
                                            <input
                                                type="password"
                                                name="confirmPassword"
                                                value={formData.confirmPassword}
                                                onChange={handleChange}
                                                className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                                                placeholder="Confirm security key"
                                            />
                                        </div>
                                    </div>
                                )}

                                {message && (
                                    <div className="p-4 rounded-xl text-xs font-bold text-center bg-red-500/10 text-red-400 border border-red-500/20">
                                        {message}
                                    </div>
                                )}

                                <button
                                    onClick={handleSubmit}
                                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-5 rounded-2xl font-black uppercase tracking-[0.2em] text-xs hover:from-purple-700 hover:to-blue-700 transition-all shadow-[0_10px_30px_rgba(138,43,226,0.3)] group"
                                >
                                    <span className="flex items-center justify-center">
                                        {isLogin ? "Login" : "Sign Up"}
                                        <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                                    </span>
                                </button>
                            </div>
                        )}
                    </div>

                    {!isForgotPassword && (
                        <div className="mt-10 text-center space-y-4">
                            {isLogin && (
                                <button
                                    onClick={toggleForgotPassword}
                                    className="text-purple-300/40 text-xs font-bold hover:text-white transition-colors uppercase tracking-[0.1em]"
                                >
                                    Lost Security Key?
                                </button>
                            )}
                            <div className="h-px bg-white/5 w-full mx-auto"></div>
                            <p className="text-purple-200/40 text-xs font-medium">
                                {isLogin ? "New user? " : "Existing operator? "}
                                <button
                                    onClick={toggleMode}
                                    className="text-purple-400 font-black hover:text-purple-300 transition-colors uppercase tracking-widest ml-1"
                                >
                                    {isLogin ? "Sign Up" : "Login"}
                                </button>
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default Login;