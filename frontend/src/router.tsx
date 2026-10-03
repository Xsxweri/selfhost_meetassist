import { createBrowserRouter, Navigate, Outlet } from "react-router";
import { useAuth } from "./store/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import MeetingList from "./pages/MeetingList";
import MeetingDetail from "./pages/MeetingDetail";
import AgentChat from "./pages/AgentChat";
import MemoryLibrary from "./pages/MemoryLibrary";
import AuditLog from "./pages/AuditLog";
import SharedMeeting from "./pages/SharedMeeting";
import Search from "./pages/Search";

function RequireAuth() {
  const token = useAuth((s) => s.token);
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/shared/:token", element: <SharedMeeting /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/meetings" replace /> },
          { path: "/meetings", element: <MeetingList /> },
          { path: "/meetings/:id", element: <MeetingDetail /> },
          { path: "/search", element: <Search /> },
          { path: "/agent", element: <AgentChat /> },
          { path: "/memory", element: <MemoryLibrary /> },
          { path: "/audit", element: <AuditLog /> },
        ],
      },
    ],
  },
]);