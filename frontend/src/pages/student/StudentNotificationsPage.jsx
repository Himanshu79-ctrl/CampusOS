import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import {
  studentNotificationApi,
  formatApiError,
} from "@/services/studentService";
import {
  Bell,
  CheckCheck,
  Check,
  Megaphone,
  BookOpen,
  Award,
  AlertTriangle,
  Calendar,
  Info,
  RefreshCw,
  Filter,
  Clock,
  Building2,
  GraduationCap,
} from "lucide-react";

export const StudentNotificationsPage = () => {
  const [activeTab, setActiveTab] = useState("notifications"); // "notifications" | "announcements"
  const [notifications, setNotifications] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const [isLoading, setIsLoading] = useState(true);
  const [isMarkingAll, setIsMarkingAll] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  // Notification Filters
  const [readFilter, setReadFilter] = useState("all"); // "all" | "unread" | "read"
  const [typeFilter, setTypeFilter] = useState("ALL");

  // Announcement Filters
  const [scopeFilter, setScopeFilter] = useState("ALL");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [notifs, unread, anncs] = await Promise.all([
        studentNotificationApi.getNotifications().catch(() => []),
        studentNotificationApi.getUnreadCount().catch(() => 0),
        studentNotificationApi.getAnnouncements().catch(() => []),
      ]);
      setNotifications(notifs || []);
      setUnreadCount(typeof unread === "number" ? unread : 0);
      setAnnouncements(anncs || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleMarkAsRead = async (notificationId) => {
    try {
      await studentNotificationApi.markAsRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      alert("Failed to mark as read: " + formatApiError(err));
    }
  };

  const handleMarkAllAsRead = async () => {
    if (unreadCount === 0) return;
    setIsMarkingAll(true);
    try {
      await studentNotificationApi.markAllAsRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
      );
      setUnreadCount(0);
    } catch (err) {
      alert("Failed to mark all as read: " + formatApiError(err));
    } finally {
      setIsMarkingAll(false);
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case "ASSIGNMENT":
        return <BookOpen className="w-5 h-5 text-amber-600" />;
      case "GRADE":
        return <Award className="w-5 h-5 text-emerald-600" />;
      case "ATTENDANCE":
        return <AlertTriangle className="w-5 h-5 text-rose-600" />;
      case "TIMETABLE":
        return <Calendar className="w-5 h-5 text-blue-600" />;
      case "ANNOUNCEMENT":
        return <Megaphone className="w-5 h-5 text-purple-600" />;
      default:
        return <Info className="w-5 h-5 text-slate-600" />;
    }
  };

  const getTypeBadge = (type) => {
    const config = {
      ASSIGNMENT: "bg-amber-50 text-amber-700 border-amber-200",
      GRADE: "bg-emerald-50 text-emerald-700 border-emerald-200",
      ATTENDANCE: "bg-rose-50 text-rose-700 border-rose-200",
      TIMETABLE: "bg-blue-50 text-blue-700 border-blue-200",
      ANNOUNCEMENT: "bg-purple-50 text-purple-700 border-purple-200",
      GENERAL: "bg-slate-100 text-slate-700 border-slate-200",
    }[type] || "bg-slate-100 text-slate-700 border-slate-200";

    return (
      <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${config}`}>
        {type}
      </span>
    );
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  // Filter notifications
  const filteredNotifications = notifications.filter((item) => {
    if (readFilter === "unread" && item.is_read) return false;
    if (readFilter === "read" && !item.is_read) return false;
    if (typeFilter !== "ALL" && item.notification_type !== typeFilter) return false;
    return true;
  });

  // Filter announcements
  const filteredAnnouncements = announcements.filter((item) => {
    if (scopeFilter !== "ALL" && item.scope !== scopeFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications & Updates"
        description="Stay informed with real-time academic alerts, assignment updates, grading notices, and official announcements."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchData}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            {activeTab === "notifications" && (
              <button
                onClick={handleMarkAllAsRead}
                disabled={isMarkingAll || unreadCount === 0}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50"
              >
                <CheckCheck className="w-4 h-4" />
                {isMarkingAll ? "Marking..." : "Mark All as Read"}
              </button>
            )}
          </div>
        }
      />

      {errorMessage && (
        <ErrorState
          title="Failed to Load Notifications"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("notifications")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "notifications"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          <Bell className="w-4 h-4" />
          Notifications
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-700 rounded-full">
              {unreadCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("announcements")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "announcements"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          <Megaphone className="w-4 h-4" />
          Announcements
          <span className="px-2 py-0.5 text-xs font-semibold bg-slate-100 text-slate-700 rounded-full">
            {announcements.length}
          </span>
        </button>
      </div>

      {/* Notifications Tab Content */}
      {activeTab === "notifications" && (
        <div className="space-y-4">
          {/* Controls / Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <Filter className="w-3.5 h-3.5" />
                Status:
              </div>
              <div className="flex items-center rounded-lg bg-slate-100 p-0.5">
                {[
                  { id: "all", label: "All" },
                  { id: "unread", label: "Unread" },
                  { id: "read", label: "Read" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setReadFilter(tab.id)}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      readFilter === tab.id
                        ? "bg-white text-slate-900 shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2 ml-2">
                <span className="text-xs font-medium text-slate-500">Type:</span>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="px-2.5 py-1 text-xs border border-slate-300 rounded-md bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="ALL">All Types</option>
                  <option value="ASSIGNMENT">Assignment</option>
                  <option value="GRADE">Grade</option>
                  <option value="ATTENDANCE">Attendance</option>
                  <option value="TIMETABLE">Timetable</option>
                  <option value="ANNOUNCEMENT">Announcement</option>
                  <option value="GENERAL">General</option>
                </select>
              </div>
            </div>

            <div className="text-xs text-slate-500">
              Showing <span className="font-semibold text-slate-700">{filteredNotifications.length}</span> of {notifications.length}
            </div>
          </div>

          {/* List of Notifications */}
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((n) => (
                <div key={n} className="p-4 bg-white border border-slate-200 rounded-xl animate-pulse space-y-2">
                  <div className="h-4 bg-slate-200 rounded w-1/3"></div>
                  <div className="h-3 bg-slate-100 rounded w-3/4"></div>
                </div>
              ))}
            </div>
          ) : filteredNotifications.length === 0 ? (
            <div className="p-12 text-center bg-white border border-slate-200 rounded-xl">
              <div className="w-12 h-12 mx-auto mb-3 bg-slate-100 rounded-full flex items-center justify-center text-slate-400">
                <Bell className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-900">No notifications found</h3>
              <p className="mt-1 text-xs text-slate-500">
                {readFilter === "unread"
                  ? "You have marked all notifications as read."
                  : "You're all caught up! Academic alerts and updates will appear here."}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredNotifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-4 rounded-xl border transition-all ${
                    notif.is_read
                      ? "bg-white border-slate-200 text-slate-700"
                      : "bg-blue-50/40 border-blue-200 shadow-xs"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3.5">
                      <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs mt-0.5">
                        {getTypeIcon(notif.notification_type)}
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className={`text-sm font-semibold ${notif.is_read ? "text-slate-900" : "text-blue-950 font-bold"}`}>
                            {notif.title}
                          </h4>
                          {!notif.is_read && (
                            <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" title="Unread" />
                          )}
                          {getTypeBadge(notif.notification_type)}
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line">
                          {notif.message}
                        </p>
                        <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400">
                          <span className="inline-flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(notif.created_at)}
                          </span>
                          {notif.is_read && notif.read_at && (
                            <span className="inline-flex items-center gap-1 text-slate-400">
                              <Check className="w-3 h-3 text-emerald-500" />
                              Read {formatDate(notif.read_at)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {!notif.is_read && (
                      <button
                        onClick={() => handleMarkAsRead(notif.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors shrink-0 shadow-2xs"
                        title="Mark this notification as read"
                      >
                        <Check className="w-3 h-3" />
                        Mark Read
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Announcements Tab Content */}
      {activeTab === "announcements" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">Scope:</span>
              <select
                value={scopeFilter}
                onChange={(e) => setScopeFilter(e.target.value)}
                className="px-2.5 py-1 text-xs border border-slate-300 rounded-md bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="ALL">All Scopes</option>
                <option value="INSTITUTION">Institution-Wide</option>
                <option value="COURSE">Course-Specific</option>
                <option value="DEPARTMENT">Department-Level</option>
              </select>
            </div>
            <div className="text-xs text-slate-500">
              Showing <span className="font-semibold text-slate-700">{filteredAnnouncements.length}</span> announcements
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[1, 2].map((n) => (
                <div key={n} className="p-5 bg-white border border-slate-200 rounded-xl animate-pulse space-y-3">
                  <div className="h-5 bg-slate-200 rounded w-1/4"></div>
                  <div className="h-3 bg-slate-100 rounded w-full"></div>
                </div>
              ))}
            </div>
          ) : filteredAnnouncements.length === 0 ? (
            <div className="p-12 text-center bg-white border border-slate-200 rounded-xl">
              <div className="w-12 h-12 mx-auto mb-3 bg-slate-100 rounded-full flex items-center justify-center text-slate-400">
                <Megaphone className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-900">No announcements published</h3>
              <p className="mt-1 text-xs text-slate-500">
                Official institution and course bulletins will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredAnnouncements.map((annc) => (
                <div
                  key={annc.id}
                  className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs hover:border-slate-300 transition-all space-y-3"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                            annc.scope === "INSTITUTION"
                              ? "bg-purple-50 text-purple-700 border-purple-200"
                              : annc.scope === "COURSE"
                              ? "bg-blue-50 text-blue-700 border-blue-200"
                              : "bg-amber-50 text-amber-700 border-amber-200"
                          }`}
                        >
                          {annc.scope === "INSTITUTION"
                            ? "Institution-Wide"
                            : annc.scope === "COURSE"
                            ? "Course Bulletin"
                            : "Department Bulletin"}
                        </span>
                        <span className="text-[11px] font-medium text-slate-500">
                          Audience: {annc.audience_type}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        {annc.title}
                      </h3>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {formatDate(annc.published_at || annc.created_at)}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        By {annc.author_role || "Administrator"}
                      </span>
                    </div>
                  </div>

                  <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line bg-slate-50 p-4 rounded-lg border border-slate-100">
                    {annc.content}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
