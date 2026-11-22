import React, { useState } from "react";
import { useNavigate, useLocation, Navigate, Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getDashboardForRole, isRouteAllowedForRole } from "@/types";
import {
  GraduationCap,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Info,
  X,
  Loader2,
  BookOpen,
} from "lucide-react";

export const LoginPage = () => {
  const { login, isAuthenticated, isLoading: authLoading, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Form State
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);

  // Status State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [showForgotModal, setShowForgotModal] = useState(false);

  // If already authenticated, redirect to their role dashboard or intended URL
  if (!authLoading && isAuthenticated && user) {
    const fromPath = location.state?.from?.pathname;
    const destination =
      fromPath && fromPath !== "/login" && isRouteAllowedForRole(fromPath, user.role)
        ? fromPath
        : getDashboardForRole(user.role);
    return <Navigate to={destination} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return; // Prevent duplicate login submissions

    setErrorMessage("");

    // Form validation
    if (!username.trim()) {
      setErrorMessage("Please enter your university username or email.");
      return;
    }
    if (!password) {
      setErrorMessage("Please enter your password.");
      return;
    }

    setIsSubmitting(true);

    try {
      const loggedInUser = await login(username.trim(), password, rememberMe);
      const fromPath = location.state?.from?.pathname;
      const targetDestination =
        fromPath && fromPath !== "/login" && isRouteAllowedForRole(fromPath, loggedInUser.role)
          ? fromPath
          : getDashboardForRole(loggedInUser.role);

      navigate(targetDestination, { replace: true });
    } catch (err) {
      const msg = err.message || "";
      if (
        err.code === "ECONNABORTED" ||
        msg.toLowerCase().includes("timeout") ||
        msg.toLowerCase().includes("took too long")
      ) {
        setErrorMessage(
          "The authentication server took too long to respond while waking up from inactivity. Please click 'Sign In' to retry."
        );
      } else if (
        msg.toLowerCase().includes("invalid credentials") ||
        msg.toLowerCase().includes("no active account")
      ) {
        setErrorMessage("Invalid username or password. Please verify your credentials and try again.");
      } else {
        setErrorMessage(msg || "Failed to sign in. Please check your network connection and try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center relative overflow-hidden font-sans">
      {/* Background Decorative Blur */}
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-indigo-200/50 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-200/50 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-5xl mx-auto p-4 sm:p-6 lg:p-8 z-10">
        <div className="bg-white rounded-3xl shadow-xl border border-slate-200/80 overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[580px]">
          {/* Left Hero Column (University Branding) */}
          <div className="lg:col-span-5 bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 text-white p-8 sm:p-12 flex flex-col justify-between relative overflow-hidden">
            <div className="relative z-10 space-y-6">
              {/* Logo & System Badge */}
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center text-white shadow-inner">
                  <GraduationCap className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="font-extrabold text-xl tracking-tight leading-none text-white">CampusOS</h1>
                  <span className="text-[11px] text-indigo-200 font-medium tracking-wide">
                    University Portal
                  </span>
                </div>
              </div>

              {/* Tagline & Description */}
              <div className="space-y-3 pt-4">
                <h2 className="text-2xl sm:text-3xl font-bold leading-tight">
                  Your Campus. <br />
                  Your Learning. <br />
                  <span className="text-indigo-200">One Platform.</span>
                </h2>
                <p className="text-indigo-100 text-xs sm:text-sm leading-relaxed">
                  Sign in with your institutional account to access your courses, class schedule, assignments, and grades.
                </p>
              </div>

              {/* User-friendly Highlights */}
              <div className="pt-2 space-y-3">
                <div className="flex items-center gap-2.5 text-xs text-indigo-100">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Interactive course modules and lesson slides</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-indigo-100">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Online homework submissions and evaluations</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-indigo-100">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Real-time attendance tracking and timetables</span>
                </div>
              </div>
            </div>

            {/* Bottom Support Contact */}
            <div className="relative z-10 pt-6 border-t border-indigo-700/50 mt-6 text-xs text-indigo-300">
              <span>Need help? Contact your campus registrar or IT office.</span>
            </div>
          </div>

          {/* Right Form Column */}
          <div className="lg:col-span-7 p-8 sm:p-12 flex flex-col justify-center bg-white">
            <div className="max-w-md w-full mx-auto space-y-6">
              {/* Header */}
              <div>
                <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Sign in to your account</h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Enter your university credentials to continue.
                </p>
              </div>

              {/* Error Alert */}
              {errorMessage && (
                <div
                  role="alert"
                  className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in"
                >
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-semibold text-xs">Authentication Failed</p>
                    <p className="mt-0.5 text-xs text-rose-700 leading-relaxed">{errorMessage}</p>
                  </div>
                </div>
              )}

              {/* Active Connection & Server Wakeup Notice */}
              {isSubmitting && (
                <div
                  role="status"
                  aria-live="polite"
                  className="p-3.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 text-xs flex items-center gap-2.5 animate-in fade-in"
                >
                  <Loader2 className="w-4 h-4 text-indigo-600 animate-spin shrink-0" />
                  <div>
                    <p className="font-semibold text-xs">Authenticating with CampusOS...</p>
                    <p className="mt-0.5 text-[11px] text-indigo-700 leading-relaxed">
                      Connecting to campus authentication service. If the server is waking up from inactivity, this may take a moment.
                    </p>
                  </div>
                </div>
              )}

              {/* Login Form */}
              <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                {/* Username Field */}
                <div>
                  <label
                    htmlFor="username"
                    className="block text-xs font-semibold text-slate-700 mb-1.5"
                  >
                    Username or College Email
                  </label>
                  <div className="relative rounded-xl shadow-xs">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      id="username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      disabled={isSubmitting}
                      placeholder="Enter your username or email"
                      className="block w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 disabled:bg-slate-100 disabled:cursor-not-allowed transition-all"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label
                      htmlFor="password"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowForgotModal(true)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative rounded-xl shadow-xs">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={isSubmitting}
                      placeholder="Enter your account password"
                      className="block w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 disabled:bg-slate-100 disabled:cursor-not-allowed transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      disabled={isSubmitting}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none transition-colors cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me Option */}
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      disabled={isSubmitting}
                      className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                    />
                    <span className="text-xs text-slate-600">Remember my session on this device</span>
                  </label>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-bold text-xs sm:text-sm shadow-sm transition-all disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Signing In...</span>
                    </>
                  ) : (
                    <>
                      <span>Sign In</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Bottom Notice */}
              <div className="pt-2 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                <span>Return to</span>
                <Link to="/" className="text-indigo-600 hover:text-indigo-800 font-semibold">
                  Welcome Page
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Institutional Forgot Password Modal */}
      {showForgotModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4"
        >
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 border border-amber-200 flex items-center justify-center">
                  <Info className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">Password Assistance</h3>
                  <p className="text-xs text-slate-500">CampusOS Academic Security</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-2 text-xs text-slate-600 leading-relaxed">
              <p>
                To protect student academic records and faculty grading accounts, password changes are managed through the university administration office.
              </p>
              <div className="pt-2 flex items-start gap-2 text-slate-700 font-medium">
                <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                <span>
                  Please reach out to your college registrar office or IT support desk with your Student Roll Number or Faculty ID to receive a password reset.
                </span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoginPage;
