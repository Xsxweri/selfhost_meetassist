import { createBrowserRouter, Navigate, Outlet } from "react-router";
import { useAuth } from "./store/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import MeetingList from "./pages/MeetingList";
import MeetingDetail from "./pages/MeetingDetail";
import Placeholder from "./pages/Placeholder";

function RequireAuth() {
  const token = useAuth((s) => s.token);
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/shared/:token", element: <Placeholder title="分享只读页（P3）" /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/meetings" replace /> },
          { path: "/meetings", element: <MeetingList /> },
          { path: "/meetings/:id", element: <MeetingDetail /> },
          { path: "/agent", element: <Placeholder title="Agent 对话（P2）" /> },
          { path: "/memory", element: <Placeholder title="记忆库（P2）" /> },
          { path: "/audit", element: <Placeholder title="审计日志（P3）" /> },
        ],
      },
    ],
  },
]);