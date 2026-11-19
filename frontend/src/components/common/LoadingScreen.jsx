import React from "react";
import { GraduationCap, Loader2 } from "lucide-react";

export const LoadingScreen = ({ message = "Authenticating session..." }) => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-4">
      <div className="flex flex-col items-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-100 animate-pulse">
          <GraduationCap className="w-8 h-8" />
        </div>
        <div className="flex items-center gap-2 text-slate-700 font-medium text-sm">
          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
          <span>{message}</span>
        </div>
      </div>
    </div>
  );
};

export default LoadingScreen;
