import type { MiddlewareNext } from "astro";
import type { APIContext } from "astro";

export function onRequest(
    context: APIContext,
    next: MiddlewareNext
): Promise<Response> | Response | Promise<void> | void {
    // intercept data from a request
    // optionally, modify the properties in `locals`

    // context.locals.title = "New title";

    // return a Response or the result of calling `next()`
    return next();
}
