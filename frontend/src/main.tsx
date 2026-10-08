import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { Provider } from "./store";
import Shell from "./components/Shell";
import NewCustomer from "./pages/NewCustomer";
import Discovery from "./pages/Discovery";
import Systems from "./pages/Systems";
import DataMapping from "./pages/DataMapping";
import Architecture from "./pages/Architecture";
import Plan from "./pages/Plan";
import Risks from "./pages/Risks";
import Validation from "./pages/Validation";
import Handoff from "./pages/Handoff";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<NewCustomer />} />
            <Route path="discovery" element={<Discovery />} />
            <Route path="systems" element={<Systems />} />
            <Route path="mapping" element={<DataMapping />} />
            <Route path="architecture" element={<Architecture />} />
            <Route path="plan" element={<Plan />} />
            <Route path="risks" element={<Risks />} />
            <Route path="validation" element={<Validation />} />
            <Route path="handoff" element={<Handoff />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </Provider>
  </StrictMode>,
);
