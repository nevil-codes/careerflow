import BoardPage from "./pages/BoardPage";
import PostingDetailPage from "./pages/PostingDetailPage";
import PostingsPage from "./pages/PostingsPage";
import ProfilePage from "./pages/ProfilePage";
import TasksPage from "./pages/TasksPage";
import { href, useRoute } from "./router";

const NAV = [
  { path: "/postings", label: "Postings" },
  { path: "/board", label: "Applications" },
  { path: "/tasks", label: "Tasks" },
  { path: "/profile", label: "Profile" },
];

function Page({ route }: { route: string }) {
  const posting = route.match(/^\/postings\/(\d+)$/);
  if (posting) return <PostingDetailPage id={Number(posting[1])} />;
  switch (route) {
    case "/postings":
      return <PostingsPage />;
    case "/board":
      return <BoardPage />;
    case "/tasks":
      return <TasksPage />;
    case "/profile":
      return <ProfilePage />;
    default:
      return <p className="text-slate-500">Page not found.</p>;
  }
}

export default function App() {
  const route = useRoute();
  const wide = route === "/board";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <nav className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2">
          <span className="mr-4 font-bold">CareerFlow</span>
          {NAV.map(({ path, label }) => {
            const active = route === path || route.startsWith(`${path}/`);
            return (
              <a
                key={path}
                href={href(path)}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 text-sm ${
                  active
                    ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                {label}
              </a>
            );
          })}
        </div>
      </nav>
      <main className={`mx-auto px-4 py-8 ${wide ? "max-w-7xl" : "max-w-4xl"}`}>
        <Page route={route} />
      </main>
    </div>
  );
}
