from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.views import (
    RegisterView,
    UserDetailView,
    UserListView,
    CreateStaffView,
    CreateStudentView,
    DeleteStudentUserView,
    CreateFacultyUserView,
    GenerateFacultySetupLinkView,
    DeleteFacultyUserView,
    VerifyPasswordSetupTokenView,
    ConfirmPasswordSetupView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/user/me/', UserDetailView.as_view(), name='user_detail'),
    path('api/users/', UserListView.as_view(), name='user_list'),
    path('api/staff/create/', CreateStaffView.as_view(), name='create_staff'),
    # Student Provisioning & Lifecycle
    path('api/students/create/', CreateStudentView.as_view(), name='create_student'),
    path('api/students/<int:pk>/', DeleteStudentUserView.as_view(), name='delete_student'),
    # Faculty Provisioning & Lifecycle
    path('api/faculty/create/', CreateFacultyUserView.as_view(), name='create_faculty'),
    path('api/faculty/setup-link/', GenerateFacultySetupLinkView.as_view(), name='faculty_setup_link'),
    path('api/faculty/<int:pk>/', DeleteFacultyUserView.as_view(), name='delete_faculty'),
    # Password Setup (Single-Use Token Workflow)
    path('api/password-setup/verify/', VerifyPasswordSetupTokenView.as_view(), name='password_setup_verify'),
    path('api/password-setup/confirm/', ConfirmPasswordSetupView.as_view(), name='password_setup_confirm'),
]
