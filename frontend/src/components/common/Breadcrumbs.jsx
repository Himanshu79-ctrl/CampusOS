import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

/**
 * Breadcrumbs Component
 * Automatically resolves path segments or renders custom breadcrumb trails.
 */
export const Breadcrumbs = ({ customCrumbs }) => {
  const location = useLocation();

  const crumbs = React.useMemo(() => {
    if (customCrumbs && Array.isArray(customCrumbs)) {
      return customCrumbs;
    }

    const segments = location.pathname.split("/").filter(Boolean);
    const resolved = [];
    let currentPath = "";

    const segmentLabels = {
      admin: "Admin",
      faculty: "Faculty",
      student: "Student",
      "super-admin": "Super Admin",
      dashboard: "Overview",
      students: "Students",
      departments: "Departments",
      courses: "Courses",
      terms: "Academic Terms",
      offerings: "Course Offerings",
      reports: "Reports & Analytics",
      announcements: "Announcements",
      content: "Course Content",
      assignments: "Assignments",
      attendance: "Attendance",
      timetable: "Timetable",
      gradebook: "Gradebook",
      materials: "Course Materials",
      grades: "My Grades",
      notifications: "Notifications",
      console: "Admin Console",
      system: "System Overview",
    };

    segments.forEach((seg) => {
      currentPath += `/${seg}`;
      resolved.push({
        label: segmentLabels[seg] || seg.charAt(0).toUpperCase() + seg.slice(1),
        path: currentPath,
      });
    });

    return resolved;
  }, [location.pathname, customCrumbs]);

  if (crumbs.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className="flex items-center text-xs text-slate-500">
      <ol className="flex items-center flex-wrap gap-1.5">
        <li>
          <Link
            to="/"
            className="flex items-center gap-1 text-slate-400 hover:text-slate-700 transition-colors"
            title="CampusOS Home"
          >
            <Home className="w-3.5 h-3.5" />
          </Link>
        </li>

        {crumbs.map((crumb, idx) => {
          const isLast = idx === crumbs.length - 1;
          return (
            <li key={crumb.path || idx} className="flex items-center gap-1.5">
              <ChevronRight className="w-3.5 h-3.5 text-slate-300 shrink-0" />
              {isLast ? (
                <span className="font-semibold text-slate-800 truncate max-w-[200px]" aria-current="page">
                  {crumb.label}
                </span>
              ) : (
                <Link
                  to={crumb.path}
                  className="hover:text-slate-800 transition-colors truncate max-w-[150px]"
                >
                  {crumb.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default Breadcrumbs;
