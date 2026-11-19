import React from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Layers, Server, ArrowLeft, RefreshCw } from "lucide-react";

export const ModulePlaceholderPage = ({
  title,
  subtitle,
  icon: Icon = Layers,
  serviceName = "CampusOS LMS Service (Port 8000)",
  expectedEndpoints = [],
  dashboardPath,
}) => {
  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        subtitle={subtitle}
        badge="Module Ready"
        badgeClasses="bg-indigo-50 text-indigo-700 border-indigo-200"
        actions={
          dashboardPath && (
            <Link
              to={dashboardPath}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors shadow-2xs"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Overview</span>
            </Link>
          )
        }
      />

      {/* Backend Integration Contract Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wider">
          <Server className="w-4 h-4 text-indigo-600" />
          <span>Connected Service: {serviceName}</span>
        </div>

        {expectedEndpoints.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Associated API Endpoints
            </span>
            <div className="flex flex-wrap gap-2">
              {expectedEndpoints.map((ep, idx) => (
                <code
                  key={idx}
                  className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 text-xs font-mono"
                >
                  {ep}
                </code>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Clean Empty State */}
      <EmptyState
        icon={Icon}
        title={`${title} Module Initialized`}
        description={`The navigation route and layout architecture for ${title} are active. Complete data workflows will render here upon module endpoint activation.`}
        actionLabel="Refresh Module"
        onAction={() => window.location.reload()}
      />
    </div>
  );
};

export default ModulePlaceholderPage;
