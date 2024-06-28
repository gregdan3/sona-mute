# Count pluralkit messages
# Not perfect; many webhook msgs exist that are not pluralkit msgs
SELECT count(Message FILTER .author.is_bot AND .author.is_webhook);

# Old, best-effort method before I had `is_webhook`
# Check for author name which is not allowed by Discord
SELECT count(Message FILTER re_test(r'[^a-z0-9_.]+', .author.name));
