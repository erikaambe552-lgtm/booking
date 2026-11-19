// Minimal hash router (no extra dependency): #/path?query
import { useEffect, useState } from "react";

export interface Route { path: string; query: URLSearchParams }

function parse(): Route {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const [path, qs] = raw.split("?");
  return { path: path || "/", query: new URLSearchParams(qs ?? "") };
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(parse);
  useEffect(() => {
    const on = () => { setRoute(parse()); window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior }); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function navigate(to: string) {
  window.location.hash = to.startsWith("#") ? to : `#${to}`;
}
