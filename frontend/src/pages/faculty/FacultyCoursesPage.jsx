import React, { useState, useEffect, useMemo } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { facultyCourseApi, formatApiError } from "@/services/facultyService";
import {
  BookOpen,
  Users,
  Search,
  Eye,
  RefreshCw,
  Calendar,
  Layers,
  Award,
  CheckCircle2,
  Clock,
  GraduationCap,
} from "lucide-react";

export const FacultyCoursesPage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals
  const [selectedOffering, setSelectedOffering] = useState(null);
  const [rosterOffering, setRosterOffering] = useState(null);
  const [rosterData, setRosterData] = useState(null);
  const [isRosterLoading, setIsRosterLoading] = useState(false);
  const [rosterError, setRosterError] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await facultyCourseApi.getMyOfferings(user?.id || user?.user_id);
      setOfferings(data || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  // View Roster
  const handleOpenRoster = async (offering) => {
    setRosterOffering(offering);
    setIsRosterLoading(true);
    setRosterError("");
    try {
      const data = await facultyCourseApi.getRoster(offering.id);
      setRosterData(data);
    } catch (err) {
      setRosterError(formatApiError(err));
    } finally {
      setIsRosterLoading(false);
    }
  };

  // Filtered offerings
  const filteredOfferings = useMemo(() => {
    return offerings.filter((o) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        o.course_id?.toLowerCase().includes(q) ||
        o.academic_term_name?.toLowerCase().includes(q) ||
        o.section?.toLowerCase().includes(q);

      const matchesStatus = statusFilter === "all" || o.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [offerings, searchQuery, statusFilter]);

  const columns = [
    {
      header: "Course & Section",
      accessor: (row) => (
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-slate-900 text-sm">{row.course_id}</span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
              Sec {row.section}
            </span>
          </div>
          <span className="text-xs text-slate-500 block mt-0.5">
            Dept: <strong className="font-mono text-slate-700">{row.department_id}</strong>
          </span>
        </div>
      ),
    },
    {
      header: "Academic Term",
      accessor: (row) => (
        <div className="text-xs text-slate-700">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-semibold block">{row.academic_term_name || `Term #${row.academic_term}`}</span>
            {row.academic_term_status && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                row.academic_term_status === "ACTIVE"
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                  : "bg-slate-100 text-slate-600 border border-slate-200"
              }`}>
                {row.academic_term_status}
              </span>
            )}
          </div>
          {row.academic_year && (
            <span className="text-[11px] text-slate-500 font-mono">AY {row.academic_year}</span>
          )}
        </div>
      ),
    },
    {
      header: "Enrollment Status",
      accessor: (row) => {
        const enrolled = row.enrolled_count ?? 0;
        const capacity = row.capacity ?? 0;
        const percent = capacity > 0 ? Math.round((enrolled / capacity) * 100) : 0;
        return (
          <div className="w-44">
            <div className="flex justify-between text-xs mb-1">
              <span className="font-semibold text-slate-700">
                {enrolled} / {capacity} Enrolled
              </span>
              <span className="text-[11px] font-mono text-slate-500">{percent}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  percent >= 90 ? "bg-amber-500" : "bg-indigo-600"
                }`}
                style={{ width: `${Math.min(100, percent)}%` }}
              />
            </div>
          </div>
        );
      },
    },
    {
      header: "Status",
      accessor: (row) => {
        const colors = {
          PUBLISHED: "bg-emerald-50 text-emerald-700 border-emerald-200",
          DRAFT: "bg-amber-50 text-amber-700 border-amber-200",
          COMPLETED: "bg-slate-100 text-slate-600 border-slate-200",
          CANCELLED: "bg-rose-50 text-rose-700 border-rose-200",
        };
        return (
          <span
            className={`text-[10px] px-2.5 py-0.5 rounded-full uppercase tracking-wider font-bold border ${
              colors[row.status] || "bg-slate-100 text-slate-600 border-slate-200"
            }`}
          >
            {row.status}
          </span>
        );
      },
      className: "w-28",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => handleOpenRoster(row)}
            title="View Enrolled Students Roster"
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
          >
            <Users className="w-3 h-3" />
            <span>Roster</span>
          </button>
          <button
            onClick={() => setSelectedOffering(row)}
            title="View Course Offering Details"
            className="p-1 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      className: "w-36 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="My Assigned Courses"
        subtitle="Manage your active course offerings, syllabus details, and enrolled student rosters."
        badge={`${offerings.length} Course Offerings`}
        actions={
          <button
            onClick={fetchData}
            title="Refresh"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by course code, term, section..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-slate-50/50"
          />
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="all">All Statuses</option>
            <option value="PUBLISHED">Published</option>
            <option value="DRAFT">Draft</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Error State */}
      {errorMessage && (
        <ErrorState
          title="Courses Load Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={filteredOfferings}
        isLoading={isLoading}
        keyExtractor={(item) => item.id}
        emptyMessage="No assigned course offerings found for your faculty account."
      />

      {/* Modal: Enrolled Students Roster */}
      {rosterOffering && (
        <Modal
          isOpen={Boolean(rosterOffering)}
          onClose={() => {
            setRosterOffering(null);
            setRosterData(null);
          }}
          title={`Enrolled Students Roster: ${rosterOffering.course_id}`}
          subtitle={`Section ${rosterOffering.section} • ${rosterOffering.academic_term_name || "Active Term"}`}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              <span className="font-semibold text-slate-700">
                Total Enrolled: <strong className="text-indigo-600 font-bold">{rosterData?.enrolled_count ?? 0}</strong> students
              </span>
              <span className="text-slate-500">
                Capacity: {rosterOffering.capacity}
              </span>
            </div>

            {rosterError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                {rosterError}
              </div>
            )}

            {isRosterLoading ? (
              <div className="py-12 text-center text-xs text-slate-400">Loading student roster...</div>
            ) : rosterData?.students?.length > 0 ? (
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden max-h-96 overflow-y-auto">
                {rosterData.students.map((st) => (
                  <div key={st.enrollment_id} className="p-3 bg-white flex items-center justify-between text-xs hover:bg-slate-50 transition-colors">
                    <div className="space-y-0.5">
                      <span className="font-bold text-slate-900 block font-mono text-sm">
                        {st.registration_number || `Student #${st.student_id}`}
                      </span>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <span>Admission Year: {st.admission_year || "—"}</span>
                        <span>&bull;</span>
                        <span>Semester: {st.current_semester || "—"}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold uppercase">
                        {st.status}
                      </span>
                      <span className="block text-[10px] text-slate-400 mt-1 font-mono">
                        {st.enrolled_at ? new Date(st.enrolled_at).toLocaleDateString() : ""}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                No students currently enrolled in this offering roster.
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => {
                  setRosterOffering(null);
                  setRosterData(null);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Offering Details */}
      {selectedOffering && (
        <Modal
          isOpen={Boolean(selectedOffering)}
          onClose={() => setSelectedOffering(null)}
          title={`Course Details: ${selectedOffering.course_id}`}
          subtitle={`Offering ID #${selectedOffering.id}`}
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
              <div>
                <span className="text-slate-400 block text-[11px]">Course Code</span>
                <span className="font-bold text-slate-800 text-sm font-mono">{selectedOffering.course_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Section</span>
                <span className="font-bold text-slate-800 text-sm font-mono">{selectedOffering.section}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Department</span>
                <span className="font-medium text-slate-800">{selectedOffering.department_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Academic Term</span>
                <span className="font-medium text-slate-800">{selectedOffering.academic_term_name || selectedOffering.academic_term}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Capacity</span>
                <span className="font-medium text-slate-800">{selectedOffering.capacity} students</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Enrolled Students</span>
                <span className="font-bold text-indigo-600">{selectedOffering.enrolled_count ?? 0}</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSelectedOffering(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default FacultyCoursesPage;
