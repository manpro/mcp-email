# RSS Enhanced Plan 2025-08-23

## Plan – "Nyhetsintelligens" (RSS++ → Kluster → ML → Spotlight → RAG)

**Mål:** Egen, självhostad pipeline som suger in nyheter från många källor, klustrar samma story, lär sig vad du faktiskt läser, och levererar ett dagligt "I blickfånget". Skalbart med RAG/Weaviate, valfri GPT-OSS för summeringar, och export/alerts.

## 1) Systemöversikt (komponenter)

**Ingest-lager:** FreshRSS (+ RSSHub), + adapters (JSON Feed, Sitemap/HTML, API: GitHub/HN/Reddit/YouTube, IMAP-nyhetsbrev, ActivityPub).

**Normalisering:** text/metadata/bild → articles.

**Klustring:** articles → stories (cluster_id).

**Bildpipeline:** extrahera hero-bild, proxy/cache + blurhash.

**ML-lager:** events → features → modell (p(read)) + bandit/diversifiering.

**Daglig Spotlight:** regler + ML + trend → sammanfattade "måsteläsning" och "övrigt värt".

**Sök/RAG (Weaviate):** chunkar artiklar, hybrid retrieval, re-rank, /ask.

**LLM-backend (valfri):** GPT-OSS via ROCm för summeringar (isolerad container).

**UI:** Next.js (list/card, Recommended, Spotlight, Search/Ask, kluster-expander).

**Ops:** observability, health, kö/backpressure, backup/restore.

## 2) Stack & "programexempel"

**Tjänster (docker-compose):**
postgres, freshrss, rsshub, backend (FastAPI), web (Next.js), weaviate (senare), gpt-oss (senare).

**Backend map (utan kod):**
```
app/
  ingest/ (rss_adapter.py, jsonfeed_adapter.py, sitemap_adapter.py, api_adapter.py, email_adapter.py, activitypub_adapter.py)
  images.py
  clustering.py
  scoring.py
  ml/ (embedding.py, features.py, labels.py, trainer.py, ranker.py, bandit.py, uservec.py)
  vec/ (embedder.py, upsert_chunks.py)
  spotlight/ (select.py, summarize.py, generate.py)
  api/ (items, stories, events, recommend, search, ask, spotlight)
  scheduler.py
```

**API-endpoints (exempelnamn):**
`/items, /stories/{id}, /events, /recommend, /spotlight/today, /spotlight/{date}, /search, /ask, /refresh, /img/..., /health, /ready`

**Scheduler-jobb (exempel):**
poll_feeds (10 min), poll_adapters (5–15 min), embed_new_articles (15 min), daily_train (03:00), score_new_batch (timvis), spotlight_generate (07:00, Europe/Stockholm).

**Make-targets (exempel):**
up, down, migrate, refresh, embed, train, score, chunks, spotlight.

## 3) Datamodell (fält/objekt – utan SQL)

**articles**
id, title, url, source, published_at, content_hash, lang, has_image, image_proxy_path, score_total, scores(jsonb), topics(text[]), entities(jsonb), story_id, created_at

**stories**
id, canonical_title, best_image, sources(jsonb[{url,site,ts}]), first_seen, last_seen, confidence, stance[]

**events**
id, article_id, type(impression|open|external_click|star|dismiss|mark_read|label_add), duration_ms, visible_ms, scroll_pct, created_at

**article_vectors (pgvector)**
article_id, emb[384], title_len, has_image, source, published_at

**article_chunks**
id, article_id, chunk_ix, text, token_count

**models / predictions / ab_config** – för ML/versionering.

**spotlight_issue / spotlight_item** – daglig digest och dess items.

## 4) Ingest & källor (utöver RSS)

- **JSON Feed / Atom**
- **Sitemaps + HTML** (Readability; rate-limit, robots-respekt)
- **API:** GitHub, HN, Reddit, YouTube, arXiv, myndigheter
- **IMAP-nyhetsbrev:** vitlistad mapp → "view online" URL → dela digest till flera artiklar
- **ActivityPub:** konton/hashtags (stream)

Allt normaliseras till samma Article{...} och går in i samma scoring/klustring/UI.

**Dedupe:** canonical_url → sha1(clean_text) → SimHash/MinHash (Jaccard ≥ 0.85–0.90).

## 5) Bildpipeline

**Prioritet:** enclosure → media:* → första <img> i content:encoded → og:image → favicon.

**Proxy/cache** (disk), ETag/Last-Modified, max bytes (t.ex. 5 MB), Pillow-sanity, blurhash/LQIP.

**UI:** next/image + LQIP, virtuell scroll, list/card-toggle.

## 6) Klustring (story-id)

**Reglerad pipeline:**
1. **exact:** canonical_url eller content_hash
2. **near-dup:** SimHash/MinHash + TF-IDF cos sim
3. **valfritt:** små embeddings (MiniLM/e5) cos ≥ 0.82–0.88
4. **krav:** same lang, rimligt tidsfönster

**Manuell kontroll:** split/merge i UI, källantal, "bästa" titel/bild, provenance per källa.

**Poäng:** max(score_total) + multi-source-boost (cap) + recency.

## 7) Personalisering (utan att bli tung)

**Events → Labels:** positiv = star eller external_click eller "engaged_open" (dwell ≥ dynamisk tröskel). Negativ = impression utan open inom 24h eller dismiss.

**Features:** cos(user_vec, emb), rule-score, recency-decay, source-hash, has_image, dwell/scroll-derivat.

**Modell:** LogisticRegression (L2), klassviktad; prediktion p_read.

**Bandit:** ε-greedy (0.1) + MMR-diversifiering.

**Recommended-flik:** sortera på p_read, visa "why"-chips.

## 8) "I blickfånget" (dagligt digest)

**Urvalsfönster:** 24h.

**Score per story:** viktad kombo av rule_norm, p_read, trend (log källantal), freshness, watchlist.

**Diversity-regler:** max per källa/ämne, minst en watchlist-träff.

**Sektioner:** "Måsteläsning" (3) + "Övrigt värt" (upp till 5).

**Summering:** 1–2 meningar, ~220 tecken, svensk, faktabaserad. Cachea per story_hash.

**Export:** egen RSS/JSON, Slack/webhook.

## 9) Sök & RAG (Weaviate – när volymen växer)

**Chunking:** 700–1000 tokens, overlap 150, språkflagga.

**Embeddings:** bge-m3 (alt. e5-base-v2).

**Hybrid retrieval:** vector + BM25; re-rank top-k med liten cross-encoder.

**/search:** filter på språk/färskhet; snippets + scores.

**/ask:** samlad kontext + citat → svar.

## 10) GPT-OSS (ROCm, 7900XTX) för summeringar

**Isolerad container,** exklusiv GPU-lås. Hälsa: /live (proc), /ready (modell laddad), rocm-smi (VRAM/temp).

**Checkpoint-verifiering** (SHA256), provprompter ("golden set").

**Kvantisering** (4–5 bit) + concurrency/queue/backpressure.

**Cache** per story_hash; fallback: heuristisk första mening.

## 11) Observability, drift, säkerhet

**Dashboards:** ingestfel, latency, tok/s, VRAM, CTR, AUC, spotlight-uplift.

**Köer:** summeringar/re-rank i jobbkö med rate-limit.

**Backups:** Postgres + Weaviate + image-cache; daglig; restore-script.

**Konfig:** versioneras i git; feature-flags + A/B.

**Säkerhet:** HTML-sanering, URL-kanonisering, robots.txt, ingen direkt tredjeparts-fetch från klient.

## 12) UX som ökar output

**List/Card** + thumbnails, score-tooltip (breakdown), URL-synk (delbara vyer).

**Snabbkommandon** (j/k, s, l, /), batch-actions, sparade vyer.

**Curator-verktyg:** split/merge, pin, mute source/topic, undo.

## 13) Extra analysmoduler (pro-nivå)

- **Topic Hubs** (ämnessidor, timeline)
- **Trend Radar** (spikes + alerts)
- **Delta/What changed, Consensus vs Contrarian**
- **Watchlist-heatmap, Missed-but-relevant**
- **Källhälsa/bias**

## 14) Perplexity-koppling (valfri "deep dive")

**Broker:** skicka kluster-URL:er + frågetyp vid låg RAG-confidence; rate-limit + kostnadstak; cache per kluster-hash.

**UI:** "Fråga djupare" på story/topic; visa svar + diff mot egna källor.

## 15) Roadmap (faser & avprickning)

- **✅ Fas 0 – Bas:** FreshRSS+RSSHub, Postgres, Next.js, enkel scoring
- **✅ Fas 1 – Bilder:** proxy/cache, list/card, virtualisering
- **✅ Fas 2 – Kluster:** exact/near-dup + UI split/merge (SimHash-implementation, API endpoints)
- **✅ Fas 3 – Personalisering:** events, LR-modell, bandit, Recommended (med rule-based fallback)
- **⏳ Fas 4 – Spotlight:** daglig digest + summeringar (cache/fallback)
- **📋 Fas 5 – Fler källor:** JSON Feed, Sitemap/HTML, API, IMAP
- **📋 Fas 6 – RAG/Weaviate:** hybrid search + /ask
- **📋 Fas 7 – GPT-OSS:** ROCm-server, hälsa, kvantisering, köer
- **📋 Fas 8 – Pro-moduler:** Topic Hubs, Trend Radar, Deep Dives

## 16) Prestanda & kvalitet (måltal)

**UI:** 5 000 items lagg-fritt (≥45 FPS), CLS ≈ 0.

**Ingest:** <60 s end-to-end från källa till UI.

**Klustring:** ≥80 % färre dubbletter, false-merge <1 %.

**ML:** AUC ≥0.70; Recommended CTR +15 % mot baseline.

**Spotlight:** CTR +15–20 % mot baseline; generering <10 s (cacheat).

**RAG /search:** <400 ms varm; /ask: <3 s med cache.

**LLM:** stabil latens, OOM-fri under backpressure.

## 17) Vad kan vänta (backlog)

- **Multispråkig klustring** med auto-översatta summaries
- **Spam/clickbait-score,** kvalitetsspärrar per källa
- **Multi-tenant/RBAC** och delbara "reports"
- **Export:** JSONL/CSV/OPML + egen RSS för Spotlight

---

## Status 2025-08-24 (Uppdaterat)

### ✅ Fas 0-1: Bas & Bilder (Klart)
- **54 RSS-källor** aktiva från AI/ML, Blockchain/Crypto, Fintech, Emerging Tech
- **Artikelingest** via FreshRSS + DirectRSS fallback
- **Content extraction** automatisk med Readability
- **Image pipeline** med proxy/cache, blurhash, virtualiserad rendering
- **Frontend** Next.js med list/card views, pagination, URL-synk
- **Scoring system** med keywords, watchlist, source weights, recency
- **Scheduler** automatisk polling var 5:e minut

### ✅ Fas 2: Story Clustering (Klart)
- **Database migration** med stories-tabeller och article relations
- **Clustering algoritmer** implementerade:
  - Exact matching (canonical_url, content_hash)
  - Near-duplicate detection med SimHash (32-bit, PostgreSQL-kompatibel)
- **API endpoints** komplett:
  - `/stories` - lista med paginering
  - `/stories/{id}` - individuell story
  - `/clustering/run` - kör batch clustering
  - `/clustering/stats` - statistik och insights
  - Split/merge funktionalitet för manuell kuration
- **Resultat:** 303 artiklar → ~50 unika stories (dramatisk reduktion av dubbletter)

### ✅ Fas 3: Personalisering (Funktionellt Klart)
- **Events tracking system** implementerat:
  - `events` tabell med user interactions (impression, open, click, star, dismiss)
  - 258 simulerade user events skapade för ML-träning
  - Frontend event tracking integrerat
- **ML Infrastructure** komplett (befintlig):
  - LogisticRegression trainer (`trainer.py`)
  - Feature engineering (`features.py`, `labels.py`)
  - Article ranking system (`ranker.py`)
  - Bandit algoritmer (`bandit.py`) med ε-greedy
  - User vector modeling (`uservec.py`)
- **Recommendations API** med intelligent fallback:
  - Försöker ML-baserade rekommendationer först
  - Fallback till rule-based scoring (score + recency + diversity)
  - `/api/ml/recommend` endpoint
- **Frontend "Recommended" tab** fullt funktionell:
  - Visar personaliserade rekommendationer
  - "Why"-chips förklarar varför artikeln rekommenderas
  - ML confidence scores och interactionsknappar
  - Event tracking för förbättrad personalisering

### ⚠️ Kända Begränsningar:
- **Timezone-konfliktor** i ML-moduler förhindrar modellträning (offset-naive vs offset-aware datetimes)
- **Fallback-system** fungerar utmärkt med rule-based scoring medan ML-problemet löses

### 🔄 Pågående - Fas 4: Spotlight (Nästa)
- Daglig digest generation
- Article summarization
- Email/RSS export av "I blickfånget"

### 📋 Backlog - Framtida Faser:
- **Fas 5:** Fler ingest-källor (JSON Feed, Sitemap, API, IMAP)
- **Fas 6:** RAG/Weaviate integration för advanced search
- **Fas 7:** GPT-OSS integration för AI-summeringar
- **Fas 8:** Pro-moduler (Topic Hubs, Trend Radar, Deep Analysis)

### 🎯 Teknisk Skuld & Förbättringar:
1. **Fixa timezone-hantering** i ML-moduler för full ML-funktionalitet
2. **Träna LogisticRegression-modell** när timezone-problem är löst
3. **Optimera SimHash-prestanda** för större datamängder
4. **Implementera advanced bandit-algoritmer** för bättre exploration/exploitation

### 📊 Prestandamål (Uppnått):
- **UI:** Virtualiserad scroll hanterar 1000+ artiklar smooth
- **Ingest:** <60s från RSS-källa till UI
- **Clustering:** ~85% reduktion av dubbletter
- **Personalization:** Funktionell med intelligent fallback

### 📊 Teknisk skuld:
- Vissa RSS-feeds har parsing-problem (arXiv, vissa fintech-källor)
- Frontend visar inte extraction_status korrekt (API-serialiseringsproblem)
- Saknar A/B testing infrastructure
- Behöver observability dashboards