import React from "react";
import { Breadcrumbs } from "./Breadcrumbs";

export const PageHeader = ({
  title,
  subtitle,
  badge,
  badgeClasses = "bg-indigo-50 text-indigo-700 border-indigo-200",
  actions,
  showBreadcrumbs = true,
}) => {
  return (
    <div className="space-y-3 pb-2 border-b border-slate-200/60">
      {showBreadcrumbs && <Breadcrumbs />}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              {title}
            </h1>
            {badge && (
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${badgeClasses}`}
              >
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="mt-1 text-xs sm:text-sm text-slate-500 max-w-3xl leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
      </div>
    </div>
  );
};

export default PageHeader;
