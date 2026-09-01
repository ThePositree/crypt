# Search And Navigation Flow

- Actor and starting state: reader knows a concept, command, setting, symptom,
  or destination but not its page.

```text
Any page
  -> press / or Ctrl/Cmd+K, or activate Search
  -> search dialog opens and receives focus
  -> type query
     -> matches: grouped results + breadcrumb + matching excerpt
        -> arrows move active result -> Enter navigates to page/anchor
     -> zero results: preserve query + suggest CLI, Configuration, Troubleshooting
  -> Escape closes and restores previous focus

Any article
  -> sidebar chooses page
  -> right contents chooses heading anchor
  -> previous/next chooses adjacent learning step
  -> browser back/forward restores route and anchor
```

- Corpus coverage: every authored title, heading, paragraph, command, setting,
  code sample, alias, and character guide metadata.
- Failure/recovery: unavailable index leaves normal navigation usable and shows
  a precise search-unavailable message.
- Endpoint: the intended page or section is reachable by pointer or keyboard.
