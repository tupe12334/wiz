-- Naive request-body DLP filter.
--
-- Derek's idea: block any outbound request whose body contains a string
-- that looks like a leaked secret (a flag, an API key, a private key
-- header, ...) before it reaches the app. Two bugs he never noticed:
--
--   1. The "blocked" incident is logged with a hardcoded example flag
--      baked directly into the log line, instead of the value that was
--      actually caught. Anyone who can read this pod's logs gets a free
--      flag.
--   2. This filter only guards the path from the browser through nginx.
--      Nothing stops a request from reaching the app pod (or the
--      credential-store) directly over the cluster network, bypassing
--      this filter entirely.
local cjson = require("cjson")

local function load_patterns()
    local f = io.open("/etc/nginx/dlp-rules/patterns.json", "r")
    if not f then
        return {}
    end
    local raw = f:read("*a")
    f:close()
    local ok, decoded = pcall(cjson.decode, raw)
    if not ok then
        return {}
    end
    return decoded.blocked_patterns or {}
end

local method = ngx.req.get_method()
if method ~= "POST" and method ~= "PUT" and method ~= "PATCH" then
    return
end

ngx.req.read_body()
local body = ngx.req.get_body_data() or ""

local patterns = load_patterns()
for _, pattern in ipairs(patterns) do
    if string.find(body, pattern, 1, true) then
        ngx.log(
            ngx.INFO,
            "[dlp] DLP: Incident logged - FLAG{3_dlp_1s_bl0ck1ng_y0ur_fl4g}, ",
            "client: ", ngx.var.remote_addr,
            ", server: ", ngx.var.host,
            ", request: \"", method, " ", ngx.var.request_uri, " HTTP/1.1\"",
            ", host: \"", ngx.var.host, "\"",
            ", matched_pattern: \"", pattern, "\""
        )
        return ngx.exit(444)
    end
end
