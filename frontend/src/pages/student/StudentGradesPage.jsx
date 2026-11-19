import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import {
  studentGradeApi,
  formatApiError,
} from "@/services/studentService";
import {
  Award,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  RefreshCw,
  FileSpreadsheet,
  Layers,
  GraduationCap,
} from "lucide-react";

export const StudentGradesPage = () => {
  const [gradesData, setGradesData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await studentGradeApi.getMyGrades();
      setGradesData(data);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const gradeRecords = gradesData?.grade_records || [];
  const finalGrades = gradesData?.final_course_grades || [];

  const columns = [
    {
      header: "Assessment Component",
      accessor: (row) => (
        <div>
          <span className="font-bold text-slate-900 block text-xs">
            {row.grade_item_name || row.item_name || `Component #${row.grade_item}`}
          </span>
          <span className="text-[11px] text-slate-500 font-mono">
            {row.course_code || `Offering #${row.course_offering || ""}`}
          </span>
        </div>
      ),
    },
    {
      header: "Score / Max Marks",
      accessor: (row) => (
        <div className="text-xs font-mono">
          <span className="font-bold text-slate-800 text-sm">
            {row.marks_obtained != null ? row.marks_obtained : "—"}
          </span>
          <span className="text-slate-400 text-[11px]"> / {row.max_marks || 100} pts</span>
        </div>
      ),
      className: "w-40",
    },
    {
      header: "Letter Grade",
      accessor: (row) => (
        <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
          {row.letter_grade || "—"}
        </span>
      ),
      className: "w-28",
    },
    {
      header: "Status",
      accessor: (row) => (
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
            row.is_published
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : "bg-amber-50 text-amber-700 border-amber-200"
          }`}
        >
          {row.is_published ? "Published" : "Provisional"}
        </span>
      ),
      className: "w-28",
    },
    {
      header: "Feedback / Remarks",
      accessor: (row) => (
        <span className="text-xs text-slate-500 italic">
          {row.feedback || "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Grades & Academic Record"
        subtitle="Continuous evaluation scores, component marks, and official final term results."
        badge={`${gradeRecords.length} Graded Items`}
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

      {/* Final Course Results Section if available */}
      {finalGrades.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <GraduationCap className="w-4 h-4 text-indigo-600" />
            <span>Final Course Grades & GPA</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {finalGrades.map((fg) => (
              <div
                key={fg.id}
                className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-between"
              >
                <div>
                  <span className="font-bold text-slate-900 font-mono text-sm block">
                    {fg.course_code || `Course #${fg.course_offering}`}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono mt-0.5 block">
                    Grade Point: <strong className="text-slate-800">{fg.grade_point ?? "—"}</strong>
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-black font-mono text-indigo-600 block">
                    {fg.letter_grade || "—"}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold uppercase">
                    {fg.status || "PASSED"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {errorMessage && (
        <ErrorState
          title="Grades Load Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Continuous Evaluation Table */}
      <div className="space-y-2">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <Award className="w-4 h-4 text-indigo-600" />
          <span>Continuous Assessment Components</span>
        </h3>
        <DataTable
          columns={columns}
          data={gradeRecords}
          isLoading={isLoading}
          keyExtractor={(item) => item.id}
          emptyMessage="No assessment grades published yet for your registered courses."
        />
      </div>
    </div>
  );
};

export default StudentGradesPage;
