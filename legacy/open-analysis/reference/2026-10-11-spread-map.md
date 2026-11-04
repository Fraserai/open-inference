11 Oct — Model Market Spread Map
Good to be back on this. I ran the full cross-comparison on today’s two charts, in the same format as the 10 September one.
The intelligence chart shows 25 models, but only 23 have a cost bar. K2 Horizon 375B (31) and Inkling (25) are excluded from everything below.
23 models → 253 unique model-vs-model comparisons.
The big result: 16 of the 23 models are economically dominated by at least one other model. Another model is as intelligent or more intelligent and cheaper.
There are 64 such dominance relationships (41 last month). Of those, 7 are exact-intelligence matches and 57 involve more intelligence for less money.
† Gemini 4 Argon is marked “Not publicly available”. It sits on the frontier, so I show the public-only alternative wherever it matters. Without it: 22 models, 15 dominated, 58 relationships.
1. The cleanest spreads: same intelligence, cheaper
Intelligence	Expensive	Cost	Cheaper	Cost	Spread	Saving
46	Grok 4.7 (xhigh)	$3.74	MiMo-V2.6-Pro	$0.13	28.77×	96.5%
38	Mistral Large 4 Preview	$1.13	GPT-6 Luna (max)	$0.07	16.14×	93.8%
53	Claude Fable 5.1 (max, fallback)	$7.63	Gemini 4 Argon†	$1.99	3.83×	73.9%
45	Qwen3.8 Max (0902)	$5.41	GLM-5.3 (max)	$2.01	2.69×	62.8%
53	Claude Fable 5.1 (max, fallback)	$7.63	GPT-6 Astra (max)	$3.26	2.34×	57.3%
44	Kimi K3 (max)	$2.00	Step 5 Preview	$1.03	1.94×	48.5%
53	GPT-6 Astra (max)	$3.26	Gemini 4 Argon†	$1.99	1.64×	39.0%
The 46-point market is the clean one: $3.74 → $0.13 with zero headline-intelligence loss.
2. The nastier spread: more intelligence AND less money
For every dominated model, this is the cheapest alternative that delivers at least the same Intelligence Index.
Current model	Intel	Cost	Better economic alternative	Intel	Cost	Intel gain	Saving
Qwen3.8 Max (0902)	45	$5.41	MiMo-V2.6-Pro	46	$0.13	+1	97.6%
Grok 4.7	46	$3.74	MiMo-V2.6-Pro	46	$0.13	0	96.5%
Mistral Large 4 Preview	38	$1.13	GPT-6 Luna	38	$0.07	0	93.8%
GLM-5.3 max	45	$2.01	MiMo-V2.6-Pro	46	$0.13	+1	93.5%
Kimi K3	44	$2.00	MiMo-V2.6-Pro	46	$0.13	+2	93.5%
Qwen3.8 27B	34	$1.01	GPT-6 Luna	38	$0.07	+4	93.1%
Gemini 3.8 Flash	41	$1.24	MiMo-V2.6-Pro	46	$0.13	+5	89.5%
Nemotron 3 Ultra	23	$0.60	GPT-6 Luna	38	$0.07	+15	88.3%
Step 5 Preview	44	$1.03	MiMo-V2.6-Pro	46	$0.13	+2	87.4%
MiniMax-M3	29	$0.51	GPT-6 Luna	38	$0.07	+9	86.3%
Claude Fable 5.1	53	$7.63	Gemini 4 Argon†	53	$1.99	0	73.9%
Muse Spark 1.3	48	$1.60	GPT-6.1 Sol	52	$0.72	+4	55.0%
DeepSeek V4.1 Flash	39	$0.27	MiMo-V2.6-Pro	46	$0.13	+7	51.9%
GLM-5.3-Flash	42	$0.25	MiMo-V2.6-Pro	46	$0.13	+4	48.0%
GPT-6 Astra	53	$3.26	Gemini 4 Argon†	53	$1.99	0	39.0%
Claude Haiku 5.5	43	$0.21*	MiMo-V2.6-Pro	46	$0.13	+3	38.1%
Public-only: Fable 5.1’s best swap becomes GPT-6 Astra (53 / $3.26, 57.3%), and Astra is no longer dominated.
Biggest pure arbitrage today: Qwen3.8 Max → MiMo-V2.6-Pro
* 45 → 46 intelligence
* $5.41 → $0.13
* +1 intelligence, 97.6% lower cost, 41.6× price spread
Last month’s biggest was 8.64×.
3. Small intelligence sacrifice → enormous savings
Allowing a maximum 3-point Intelligence Index drop:
Expensive model	Intel	Cost	Alternative	Intel	Cost	Score loss	Saving
Gemini 3.8 Flash	41	$1.24	GPT-6 Luna	38	$0.07	-3	94.4% / 17.7×
Muse Spark 1.3	48	$1.60	MiMo-V2.6-Pro	46	$0.13	-2	91.9% / 12.3×
Claude Fable 5.1	53	$7.63	GPT-6.1 Sol	52	$0.72	-1	90.6% / 10.6×
GPT-6 Astra	53	$3.26	GPT-6.1 Sol	52	$0.72	-1	77.9% / 4.53×
DeepSeek V4.1 Flash	39	$0.27	GPT-6 Luna	38	$0.07	-1	74.1% / 3.86×
Gemini 4 Argon†	53	$1.99	GPT-6.1 Sol	52	$0.72	-1	63.8% / 2.76×
Claude Sonnet 5.5	56	$5.46	Gemini 4 Argon†	53	$1.99	-3	63.6% / 2.74×
Claude Opus 5.5	58	$5.98	Claude Sonnet 5.5	56	$5.46	-2	8.7% / 1.10×
Public-only, Sonnet 5.5’s 3-point swap is GPT-6 Astra (53 / $3.26, 40.3%).
The step from 53 to 52 is the most expensive single point on the board: giving it up saves 64–91%.
Loosen to 4–6 points and the top of the market opens up:
Expensive model	Intel	Cost	Alternative	Intel	Cost	Score loss	Saving
Claude Opus 5.5	58	$5.98	GPT-6.1 Sol	52	$0.72	-6	88.0% / 8.31×
Claude Sonnet 5.5	56	$5.46	GPT-6.1 Sol	52	$0.72	-4	86.8% / 7.58×
GPT-6.1 Sol	52	$0.72	MiMo-V2.6-Pro	46	$0.13	-6	81.9% / 5.54×
GLM-5.3-Flash	42	$0.25	GPT-6 Luna	38	$0.07	-4	72.0% / 3.57×
Claude Haiku 5.5	43	$0.21*	GPT-6 Luna	38	$0.07	-5	66.7% / 3.00×
4. Absolute dollar spread
Switch	Saving/task	Intelligence
Claude Fable 5.1 → Gemini 4 Argon†	$5.64	53 → 53
Qwen3.8 Max → MiMo-V2.6-Pro	$5.28	45 → 46
Claude Fable 5.1 → GPT-6 Astra	$4.37	53 → 53
Grok 4.7 → MiMo-V2.6-Pro	$3.61	46 → 46
Claude Fable 5.1 → Claude Sonnet 5.5	$2.17	53 → 56
GLM-5.3 max → MiMo-V2.6-Pro	$1.88	45 → 46
Kimi K3 → MiMo-V2.6-Pro	$1.87	44 → 46
GPT-6 Astra → Gemini 4 Argon†	$1.27	53 → 53
Gemini 3.8 Flash → MiMo-V2.6-Pro	$1.11	41 → 46
Mistral Large 4 Preview → GPT-6 Luna	$1.06	38 → 38
The two rankings split again:
* Percentage arbitrage: Qwen3.8 Max → MiMo (97.6%).
* Absolute-dollar arbitrage: Fable 5.1 → Argon† or Astra.
The single largest dollar saving is not a dominance swap: Fable 5.1 → GPT-6.1 Sol saves $6.91 per task for a 1-point drop.
5. The actual economic frontier
Out of 23 models, only 7 are non-dominated on cost + intelligence.
Economic tier	Intelligence	Cost/task
Muse Glimmer	17	$0.06
GPT-6 Luna	38	$0.07
MiMo-V2.6-Pro	46	$0.13
GPT-6.1 Sol	52	$0.72
Gemini 4 Argon†	53	$1.99
Claude Sonnet 5.5	56	$5.46
Claude Opus 5.5	58	$5.98
Public-only, GPT-6 Astra (53 / $3.26) takes Argon’s slot.
The shape:
* 17 → 38 intelligence: only +$0.01
* 38 → 46: only +$0.06
* 46 → 52: +$0.59 (5.5× the money for +6)
* 52 → 53: +$1.27 for one point (+$2.54 via Astra if you need a public model)
* 53 → 56: +$3.47
* 56 → 58: +$0.52
The price cliff has moved. Last month it sat after 42 ($0.25 → $1.60). Today 46 costs $0.13 and 52 costs $0.72. The cliff is now after 52: getting to 56 costs $5.46, which is 7.6× more money for +4 points.
6. Cheapest way to buy an intelligence level
Required intelligence	Cheapest qualifying model	Actual intelligence	Cost
≥17	Muse Glimmer	17	$0.06
≥23	GPT-6 Luna	38	$0.07
≥30	GPT-6 Luna	38	$0.07
≥38	GPT-6 Luna	38	$0.07
≥40	MiMo-V2.6-Pro	46	$0.13
≥42	MiMo-V2.6-Pro	46	$0.13
≥44	MiMo-V2.6-Pro	46	$0.13
≥46	MiMo-V2.6-Pro	46	$0.13
≥48	GPT-6.1 Sol	52	$0.72
≥50	GPT-6.1 Sol	52	$0.72
≥52	GPT-6.1 Sol	52	$0.72
≥53	Gemini 4 Argon† (public: GPT-6 Astra)	53	$1.99 ($3.26)
≥56	Claude Sonnet 5.5	56	$5.46
≥58	Claude Opus 5.5	58	$5.98
The routing concept:
* “I need ≥40 intelligence.” → MiMo-V2.6-Pro, $0.13.
* “I need ≥47.” → GPT-6.1 Sol, $0.72.
* “I need frontier 58.” → Opus 5.5, $5.98.
7. Open-source-only arbitrage
Today’s charts don’t mark open vs proprietary, so I took the labels from Artificial Analysis’s open-weights page. Nine open models have a cost bar.
The open frontier has collapsed to two models: Muse Glimmer → MiMo-V2.6-Pro. Last month it was four. MiMo dominates every other open model on the chart:
Expensive open model	Intel	Cost	Better open model	Intel	Cost	Saving
GLM-5.3 max	45	$2.01	MiMo-V2.6-Pro	46	$0.13	93.5%
Kimi K3	44	$2.00	MiMo-V2.6-Pro	46	$0.13	93.5%
Qwen3.8 27B	34	$1.01	MiMo-V2.6-Pro	46	$0.13	87.1%
Nemotron 3 Ultra	23	$0.60	MiMo-V2.6-Pro	46	$0.13	78.3%
MiniMax-M3	29	$0.51	MiMo-V2.6-Pro	46	$0.13	74.5%
DeepSeek V4.1 Flash	39	$0.27	MiMo-V2.6-Pro	46	$0.13	51.9%
GLM-5.3-Flash	42	$0.25	MiMo-V2.6-Pro	46	$0.13	48.0%
Three classification notes:
* Step 5 Preview and Mistral Large 4 Preview are API-only today, so I counted them as proprietary. Both have weights announced for later this month, per secondary reports. If they land, both join this table and both are still dominated by MiMo.
* Qwen3.8 Max (0902) is the hosted API model, not the open 2.4T checkpoint that appeared last month as “Qwen3.8 24T A95B”.
* Self-hosting is still a separate spread these screenshots don’t contain, so no number for it.
8. Open vs closed isn’t actually the story
Sometimes open destroys proprietary:
* Qwen3.8 Max 45 / $5.41 → MiMo 46 / $0.13
* Grok 4.7 46 / $3.74 → MiMo 46 / $0.13
* Gemini 3.8 Flash 41 / $1.24 → MiMo 46 / $0.13
* Claude Haiku 5.5 43 / $0.21* → MiMo 46 / $0.13
Sometimes proprietary destroys open:
* Qwen3.8 27B 34 / $1.01 → GPT-6 Luna 38 / $0.07
* Nemotron 3 Ultra 23 / $0.60 → GPT-6 Luna 38 / $0.07
* MiniMax-M3 29 / $0.51 → GPT-6 Luna 38 / $0.07
* GLM-5.3 max 45 / $2.01 → GPT-6.1 Sol 52 / $0.72
* Kimi K3 44 / $2.00 → GPT-6.1 Sol 52 / $0.72
One structural point: the open ceiling is 46. Everything from 47 to 58 is proprietary. Same rule as before: no ideological preference, just hunt the spread.
9. Same-family pricing weirdness
Family	Lower-cost model	Higher tier	What happens
GLM	Flash: 42 / $0.25	Max: 45 / $2.01	8.04× cost for +3 intelligence
OpenAI	Luna: 38 / $0.07	Sol: 52 / $0.72	10.29× cost for +14
OpenAI	Sol: 52 / $0.72	Astra: 53 / $3.26	4.53× cost for +1
Qwen	27B: 34 / $1.01	Max: 45 / $5.41	5.36× cost for +11
Gemini	3.8 Flash: 41 / $1.24	4 Argon†: 53 / $1.99	1.60× cost for +12
Muse	Glimmer: 17 / $0.06	Spark: 48 / $1.60	26.67× cost for +31
Claude	Haiku 5.5: 43 / $0.21*	Sonnet 5.5: 56 / $5.46	26.0× cost for +13
Claude	Sonnet 5.5: 56 / $5.46	Opus 5.5: 58 / $5.98	1.10× cost for +2
The Claude family still has a price inversion, now with a different victim:
* Claude Fable 5.1: 53 intelligence / $7.63
* Claude Sonnet 5.5: 56 / $5.46
* Claude Opus 5.5: 58 / $5.98
Fable 5.1 is less intelligent and more expensive than both. It is the most expensive model on the chart and is dominated by five others.
OpenAI has a near-inversion: Astra costs 4.53× Sol for one extra point.
10. The models doing the most damage
Model	Intelligence	Cost	Models it dominates
MiMo-V2.6-Pro	46	$0.13	13
GPT-6.1 Sol	52	$0.72	9
Claude Haiku 5.5	43	$0.21*	7 (itself dominated by MiMo)
Gemini 4 Argon†	53	$1.99	6
GLM-5.3-Flash	42	$0.25	6 (itself dominated)
GPT-6 Luna	38	$0.07	4
Muse Spark 1.3	48	$1.60	4 (itself dominated)
DeepSeek V4.1 Flash	39	$0.27	4 (itself dominated)
GPT-6 Astra	53	$3.26	3
Step 5 Preview	44	$1.03	3 (itself dominated)
Claude Sonnet 5.5 / Opus 5.5	56 / 58	$5.46 / $5.98	1 each (Fable 5.1)
MiMo-V2.6-Pro is the standout economic weapon today: at $0.13 it wipes out 13 of the other 22 models. GLM-5.3-Flash held that title last month with 9 and is now dominated itself.
What moved since 10 Sep
* Frontier: only Muse Glimmer survives from last month’s six. GLM-5.3-Flash and Muse Spark are now dominated, and Astra survives only if you exclude Argon.
* Ceiling: 53 → 58.
* Price of ≥42: $0.25 → $0.13. Price of ≥48: $1.60 → $0.72, and it now buys 52.
* Biggest strict-dominance spread: 8.64× → 41.6×.
* Carried-over models: Fable 5.1, Astra, Spark, GLM-5.3 max, Kimi K3, GLM-5.3-Flash and Gemini 3.8 Flash read identically. Qwen3.8 27B went $0.82 → $1.01 and Nemotron $0.58 → $0.60.
* One-point drifts: Glimmer 18 → 17, MiniMax-M3 30 → 29, Inkling 26 → 25. I can’t tell which index version the September snapshot used, so treat these as possible version noise.
What the automated system should hunt every morning
The 12 spread classes are unchanged:
1. Exact-intelligence spread
2. Strict dominance spread
3. Near-parity spread
4. Absolute-dollar spread
5. Percentage spread
6. Open-source-only spread
7. Open ↔ proprietary spread
8. Provider/family spread
9. Frontier spread
10. Price inversion
11. Dominance count
12. Self-hosted spread
Today suggests a 13th: availability-adjusted spread. Run every table with and without non-public models, because Argon alone changes the ≥53 price from $3.26 to $1.99.
Headline: 70% of the models shown — 16 out of 23 — are dominated on headline intelligence + cost by at least one other model.
Caveats
* Haiku 5.5’s $0.21*: the asterisk is on AA’s chart, but the footnote isn’t in the screenshot and I couldn’t find its definition. Treat that cost as provisional.
* Open/closed labels: these come from AA’s open-weights page and web reports, not from your screenshots. License details for DeepSeek V4.1 Flash and the two pending weight releases rest on secondary sources.
* Same caveat as last month: this is dominance on AA’s aggregate index and cost-per-task metric. It doesn’t prove two models are interchangeable for a given workload; it’s the first-pass detector, with workload-specific requirements as the second filter.
