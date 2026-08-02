// Dev-only entry: renders the results view standalone (npm run dev).
// The production build uses main.tsx as a UMD library entry instead;
// /datacontract/api/results is served from dev-fixtures/results.json
// by the mock plugin in vite.config.ts.
import { createRoot } from "react-dom/client";

import DataContractResults from "./main";

createRoot(document.getElementById("root")!).render(<DataContractResults />);
