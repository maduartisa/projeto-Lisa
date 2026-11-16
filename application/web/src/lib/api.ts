export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function api<T>(
  path: string,
  token?: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const result: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    let message = `Erro na solicitação (${response.status}).`;

    if (typeof result === "string" && result) {
      message = result;
    } else if (result && typeof result === "object") {
      const body = result as { detail?: unknown; message?: unknown };
      if (typeof body.detail === "string") message = body.detail;
      else if (typeof body.message === "string") message = body.message;
      else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((item) =>
            item && typeof item === "object" && "msg" in item
              ? String(item.msg)
              : String(item),
          )
          .join("; ");
      }
    }

    throw new ApiError(message, response.status);
  }

  return result as T;
}

export function queryString(
  values: Record<string, string | number | boolean | null | undefined>,
): string {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }

  const query = params.toString();
  return query ? `?${query}` : "";
}
