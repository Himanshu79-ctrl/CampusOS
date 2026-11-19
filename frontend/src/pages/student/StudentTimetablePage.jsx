import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import {
  studentTimetableApi,
  formatApiError,
} from "@/services/studentService";
import {
  Clock,
  MapPin,
  Building2,
  Calendar,
  BookOpen,
  RefreshCw,
} from "lucide-react";

const DAYS_OF_WEEK = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
];

export const StudentTimetablePage = () => {
  const [timetableEntries, setTimetableEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await studentTimetableApi.getMyTimetable();
      setTimetableEntries(data || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const entriesByDay = useMemo(() => {
    const map = {};
    DAYS_OF_WEEK.forEach((d) => (map[d] = []));
    timetableEntries.forEach((entry) => {
      const day = entry.day_of_week?.toUpperCase();
      if (map[day]) {
        map[day].push(entry);
      }
    });
    // Sort each day's entries by start time
    Object.keys(map).forEach((d) => {
      map[d].sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));
    });
    return map;
  }, [timetableEntries]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Class Timetable"
        subtitle="Your personalized weekly lecture schedule, laboratory venues, and timings across registered courses."
        badge={`${timetableEntries.length} Classes Weekly`}
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

      {errorMessage && (
        <ErrorState
          title="Timetable Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading student timetable...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {DAYS_OF_WEEK.map((day) => {
            const slots = entriesByDay[day] || [];
            return (
              <div
                key={day}
                className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden flex flex-col"
              >
                {/* Day Header */}
                <div className="p-3.5 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                  <span className="font-bold text-slate-800 text-xs uppercase tracking-wider">
                    {day}
                  </span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-600">
                    {slots.length} {slots.length === 1 ? "Class" : "Classes"}
                  </span>
                </div>

                {/* Day Slots */}
                <div className="p-3.5 space-y-2.5 flex-1">
                  {slots.length === 0 ? (
                    <p className="text-xs text-slate-400 italic py-6 text-center">No classes scheduled</p>
                  ) : (
                    slots.map((slot) => (
                      <div
                        key={slot.id}
                        className="p-3 rounded-xl border border-slate-200/70 bg-slate-50/50 hover:bg-slate-50 hover:border-indigo-200 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-bold text-slate-900 text-xs font-mono">
                              {slot.course_code || slot.course_id || `Offering #${slot.course_offering}`}
                            </span>
                            {slot.section && (
                              <span className="text-[10px] ml-1.5 px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 font-semibold">
                                Sec {slot.section}
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] uppercase font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                            {slot.entry_type}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 text-xs text-indigo-700 font-mono font-semibold mt-1.5">
                          <Clock className="w-3.5 h-3.5 text-indigo-500" />
                          <span>
                            {slot.start_time} &rarr; {slot.end_time}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-200/50">
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-400" />
                            <span>Room: {slot.room}</span>
                          </div>
                          {slot.building && (
                            <span className="text-[10px] text-slate-400 truncate max-w-28">
                              {slot.building}
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StudentTimetablePage;
