import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { passwordSetupApi, formatApiError } from "@/services/adminService";
import {
  GraduationCap,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Check,
  User,
} from "lucide-react";

export const PasswordSetupPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get("uid") || "";
  const token = searchParams.get("token") || "";

  // Token Verification State
  const [isVerifying, setIsVerifying] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [studentInfo, setStudentInfo] = useState(null);
  const [verificationError, setVerificationError] = useState("");

  // Form State
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const verifyToken = async () => {
      if (!uid || !token) {
        if (isMounted) {
          setIsVerifying(false);
          setTokenValid(false);
          setVerificationError(
            "Missing password setup credentials in URL. Please use the complete link provided by your university administrator."
          );
        }
        return;
      }

      try {
        const data = await passwordSetupApi.verify(uid, token);
        if (isMounted) {
          setTokenValid(data.valid);
          setStudentInfo(data);
        }
      } catch (err) {
        if (isMounted) {
          setTokenValid(false);
          setVerificationError(
            err.response?.data?.message ||
              "This password setup link is invalid, expired, or has already been used. Please request a new setup link from your administrator."
          );
        }
      } finally {
        if (isMounted) setIsVerifying(false);
      }
    };

    verifyToken();
    return () => {
      isMounted = false;
    };
  }, [uid, token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!password) {
      setFormError("Please enter a new password.");
      return;
    }
    if (password.length < 8) {
      setFormError("Password must be at least 8 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      setFormError("Passwords do not match. Please re-enter.");
      return;
    }

    setIsSubmitting(true);
    try {
      await passwordSetupApi.confirm(uid, token, password);
      setIsSuccess(true);
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasMinLength = password.length >= 8;
  const passwordsMatch = password && confirmPassword && password === confirmPassword;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center relative overflow-hidden font-sans">
      {/* Background Decorative Blur */}
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-indigo-200/50 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-200/50 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-xl mx-auto p-4 sm:p-6 z-10">
        <div className="bg-white rounded-3xl shadow-xl border border-slate-200/80 p-6 sm:p-10 space-y-6">
          {/* Header Branding */}
          <div className="text-center space-y-2">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-600 text-white shadow-md shadow-indigo-200">
              <GraduationCap className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">CampusOS</h1>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
              {studentInfo?.role === "faculty"
                ? "Faculty Account Password Setup"
                : studentInfo?.role === "student"
                ? "Student Account Password Setup"
                : "Account Password Setup"}
            </p>
          </div>

          {/* Loading State */}
          {isVerifying && (
            <div className="py-12 flex flex-col items-center justify-center space-y-3 text-slate-500">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              <p className="text-xs font-medium">Verifying your secure setup link...</p>
            </div>
          )}

          {/* Invalid / Expired Token */}
          {!isVerifying && !tokenValid && !isSuccess && (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto border border-rose-100">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h2 className="text-base font-bold text-slate-900">Link Invalid or Expired</h2>
                <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
                  {verificationError}
                </p>
              </div>
              <div className="pt-4">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-colors"
                >
                  <span>Return to Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {/* Setup Success State */}
          {isSuccess && (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-100">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h2 className="text-base font-bold text-slate-900">Password Configured Successfully!</h2>
                <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
                  Your new password has been secured. You can now access your courses, academic schedules, attendance, and learning materials.
                </p>
              </div>
              <div className="pt-4">
                <button
                  type="button"
                  onClick={() => navigate("/login")}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-colors cursor-pointer"
                >
                  <span>Proceed to Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Valid Token - Setup Password Form */}
          {!isVerifying && tokenValid && !isSuccess && (
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Student Greeting */}
              <div className="p-3.5 rounded-2xl bg-indigo-50/70 border border-indigo-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-white text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-200">
                  <User className="w-4 h-4" />
                </div>
                <div className="min-w-0 text-xs">
                  <span className="font-bold text-slate-900 block truncate">
                    Welcome, {studentInfo?.first_name || studentInfo?.username}!
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Account: {studentInfo?.username} &bull; {studentInfo?.email}
                  </span>
                </div>
              </div>

              {formError && (
                <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Password Input */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  New Password *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Create a strong password"
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password Input */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Confirm Password *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat your new password"
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Password Quality Criteria */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1.5 text-[11px]">
                <div className={`flex items-center gap-1.5 ${hasMinLength ? "text-emerald-700 font-semibold" : "text-slate-500"}`}>
                  <Check className={`w-3.5 h-3.5 ${hasMinLength ? "text-emerald-600" : "text-slate-400"}`} />
                  <span>At least 8 characters long</span>
                </div>
                <div className={`flex items-center gap-1.5 ${passwordsMatch ? "text-emerald-700 font-semibold" : "text-slate-500"}`}>
                  <Check className={`w-3.5 h-3.5 ${passwordsMatch ? "text-emerald-600" : "text-slate-400"}`} />
                  <span>Passwords match</span>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !hasMinLength || !passwordsMatch}
                className="w-full py-2.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Securing Password...</span>
                  </>
                ) : (
                  <>
                    <span>Set Password & Activate Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default PasswordSetupPage;
