import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";
import ProfilePage from "./pages/ProfilePage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ProfilePage />
  </StrictMode>,
);
