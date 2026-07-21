import {
  createRootRoute,
  createRoute,
  createRouter,
  Navigate,
} from "@tanstack/react-router";
import { AppShell } from "@/components/shell/app-shell";
import { MarketsPage } from "@/pages/markets-page";
import { WorkspacePage } from "@/pages/workspace-page";
import { ResearchPage } from "@/pages/research-page";
const rootRoute = createRootRoute({ component: AppShell });
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: () => <Navigate to="/markets" />,
});
const marketsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/markets",
  component: MarketsPage,
});
const workspaceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workspace",
  component: WorkspacePage,
});
const researchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/research",
  component: ResearchPage,
});
const routeTree = rootRoute.addChildren([
  indexRoute,
  marketsRoute,
  workspaceRoute,
  researchRoute,
]);
export const router = createRouter({ routeTree, defaultPreload: "intent" });
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
