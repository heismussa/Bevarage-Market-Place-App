import type { paths } from "./schema.js";

type HealthResponse =
  paths["/api/v1/health/"]["get"]["responses"][200]["content"]["application/json"];

const sampleHealthResponse: HealthResponse = {
  status: "ok",
};

export { sampleHealthResponse };
