import {
  LayoutDashboard,
  Users,
  GraduationCap,
  Building2,
  BookOpen,
  Calendar,
  Layers,
  BarChart3,
  Megaphone,
  FileText,
  CheckSquare,
  Clock,
  Award,
  Bell,
  ShieldCheck,
  Server,
} from "lucide-react";

/**
 * Navigation configuration for Admin Role
 */
export const ADMIN_NAV_ITEMS = [
  { label: "Overview", path: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Students", path: "/admin/students", icon: Users },
  { label: "Faculty", path: "/admin/faculty", icon: GraduationCap },
  { label: "Departments", path: "/admin/departments", icon: Building2 },
  { label: "Courses", path: "/admin/courses", icon: BookOpen },
  { label: "Academic Terms", path: "/admin/terms", icon: Calendar },
  { label: "Course Offerings", path: "/admin/offerings", icon: Layers },
  { label: "Reports", path: "/admin/reports", icon: BarChart3 },
  { label: "Announcements", path: "/admin/announcements", icon: Megaphone },
];

/**
 * Navigation configuration for Faculty Role
 */
export const FACULTY_NAV_ITEMS = [
  { label: "Overview", path: "/faculty/dashboard", icon: LayoutDashboard },
  { label: "My Courses", path: "/faculty/courses", icon: BookOpen },
  { label: "Course Content", path: "/faculty/content", icon: FileText },
  { label: "Assignments", path: "/faculty/assignments", icon: CheckSquare },
  { label: "Attendance", path: "/faculty/attendance", icon: Calendar },
  { label: "Timetable", path: "/faculty/timetable", icon: Clock },
  { label: "Gradebook", path: "/faculty/gradebook", icon: Award },
  { label: "Announcements", path: "/faculty/announcements", icon: Megaphone },
];

/**
 * Navigation configuration for Student Role
 */
export const STUDENT_NAV_ITEMS = [
  { label: "Overview", path: "/student/dashboard", icon: LayoutDashboard },
  { label: "My Courses", path: "/student/courses", icon: BookOpen },
  { label: "Course Materials", path: "/student/materials", icon: FileText },
  { label: "Assignments", path: "/student/assignments", icon: CheckSquare },
  { label: "Attendance", path: "/student/attendance", icon: Calendar },
  { label: "Timetable", path: "/student/timetable", icon: Clock },
  { label: "My Grades", path: "/student/grades", icon: Award },
  { label: "Notifications", path: "/student/notifications", icon: Bell },
];

/**
 * Navigation configuration for Super Admin Role
 */
export const SUPER_ADMIN_NAV_ITEMS = [
  { label: "Overview", path: "/super-admin/dashboard", icon: LayoutDashboard },
  { label: "Students", path: "/super-admin/students", icon: Users },
  { label: "Faculty", path: "/super-admin/faculty", icon: GraduationCap },
  { label: "Departments", path: "/super-admin/departments", icon: Building2 },
  { label: "Courses", path: "/super-admin/courses", icon: BookOpen },
  { label: "Academic Terms", path: "/super-admin/terms", icon: Calendar },
  { label: "Course Offerings", path: "/super-admin/offerings", icon: Layers },
  { label: "Reports", path: "/super-admin/reports", icon: BarChart3 },
  { label: "Announcements", path: "/super-admin/announcements", icon: Megaphone },
];

export const getNavItemsForRole = (role) => {
  switch (role) {
    case "admin":
      return ADMIN_NAV_ITEMS;
    case "faculty":
      return FACULTY_NAV_ITEMS;
    case "student":
      return STUDENT_NAV_ITEMS;
    case "super_admin":
      return SUPER_ADMIN_NAV_ITEMS;
    default:
      return [];
  }
};
