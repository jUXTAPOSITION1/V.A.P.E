# Research Leads

Saved output of `agents/web_sourcer.py`'s crawler (`WebSourcer.save_leads()` /
`python -m agents.web_sourcer research "..." --save <label>`). Each file is one
crawl run: `<label>-<UTC timestamp>.json` containing the query, a count, and
the list of leads (`url`, `domain`, scrape `provider`, extracted `content`,
tagged `entities`, `fetched_at`).

Not every research call writes here — `research()`/`process_query()`/
`intelligent_crawl()` just return the leads in memory; saving to this
directory is an explicit, separate step so a one-off lookup doesn't silently
accumulate files. See `agents/web_sourcer.py`'s module docstring for the full
design (robots.txt compliance, cross-run dedup + cache under
`data/cache/web_sourcer/`, LLM-scored link-following, `config/sources.yaml`
integration).
