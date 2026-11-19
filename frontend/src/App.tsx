import { Footer, Navbar, Splash } from "./components/Layout";
import { Empty, Spinner } from "./components/Cards";
import { AuthProvider, useAuth } from "./lib/auth";
import { RealtimeProvider, Toaster } from "./lib/realtime";
import { useRoute } from "./lib/router";
import type { Role } from "./lib/types";
import Home from "./pages/Home";
import Explore from "./pages/Explore";
import Details from "./pages/Details";
import HowItWorks from "./pages/HowItWorks";
import { Login, Register } from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import Operator from "./pages/Operator";
import Admin from "./pages/Admin";
import type { ReactNode } from "react";

function Guard({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="page container"><Spinner /></div>;
  if (!user) return <div className="page container"><Empty title="Please log in"><a className="pill pill-solid" href="#/login">Log in</a></Empty></div>;
  if (roles && !roles.includes(user.role)) return <div className="page container"><Empty title="Not allowed">Your account role can't open this page.</Empty></div>;
  return <>{children}</>;
}

function Routes() {
  const route = useRoute();
  const { path } = route;
  let page: ReactNode;
  const detail = path.match(/^\/destinations\/([\w-]+)$/);
  if (path === "/") page = <Home />;
  else if (path === "/explore") page = <Explore route={route} />;
  else if (detail) page = <Details slug={detail[1]} route={route} />;
  else if (path === "/how-it-works") page = <HowItWorks />;
  else if (path === "/login") page = <Login route={route} />;
  else if (path === "/register") page = <Register />;
  else if (path === "/dashboard") page = <Guard><Dashboard /></Guard>;
  else if (path === "/operator") page = <Guard roles={["VENUE_OPERATOR", "GUIDE", "ADMIN"]}><Operator /></Guard>;
  else if (path === "/admin") page = <Guard roles={["ADMIN"]}><Admin /></Guard>;
  else page = <div className="page container"><Empty title="Page not found"><a href="#/">Back home</a></Empty></div>;

  return (
    <>
      <Navbar path={path} />
      <main key={path} className="fade-in">{page}</main>
      <Footer />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <RealtimeProvider>
        <Splash />
        <Routes />
        <Toaster />
      </RealtimeProvider>
    </AuthProvider>
  );
}
