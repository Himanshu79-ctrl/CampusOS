import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export const ErrorState = ({
  title = "Failed to load data",
  message = "An error occurred while communicating with the microservice.",
  onRetry,
}) => {
  return (
    <div className="bg-rose-50/50 rounded-2xl border border-rose-200/80 p-8 text-center flex flex-col items-center justify-center max-w-lg mx-auto my-6">
      <div className="w-12 h-12 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center mb-3">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-bold text-rose-900">{title}</h3>
      <p className="text-xs sm:text-sm text-rose-700 mt-1 max-w-md leading-relaxed">
        {message}
      </p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-rose-800 bg-white hover:bg-rose-100 border border-rose-300 transition-colors cursor-pointer shadow-2xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Try Again</span>
        </button>
      )}
    </div>
  );
};

export default ErrorState;
