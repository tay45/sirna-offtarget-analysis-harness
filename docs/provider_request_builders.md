# Provider Request Builders

Provider request construction is typed and provider-specific under
`sirna_offtarget.pathway.fetch`. Builders capture endpoint, method, query
parameters, body, headers, content type, pagination mode, release discovery,
timeout, retry statuses, rate-limit behavior, and response validation.

Endpoint overrides remain available for mirrors and tests, but users do not need
to manually assemble provider-specific URLs.
