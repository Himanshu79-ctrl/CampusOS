import React from "react";
import { Loader2 } from "lucide-react";

export const LoadingState = ({ message = "Loading records..." }) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center flex flex-col items-center justify-center my-4">
      <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
      <p className="text-xs sm:text-sm font-medium text-slate-600">{message}</p>
    </div>
  );
};

export default LoadingState;
