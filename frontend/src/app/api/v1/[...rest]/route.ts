import { fail, preflight } from "@/lib/api/envelope";

const notFound = (_req: Request) => fail(404, "not_found", "No such endpoint. See /developers for the list.");

export const GET = notFound;
export const POST = notFound;
export const PUT = notFound;
export const DELETE = notFound;
export const OPTIONS = preflight;
